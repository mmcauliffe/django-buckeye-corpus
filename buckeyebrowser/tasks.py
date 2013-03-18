'''
Created on 2012-08-24

@author: michael
'''
import os
import re
import math

from celery import task,chord,group
from celery.signals import task_success
from celery.utils.log import get_task_logger

from django.db.models import Q
from django.core.management import call_command
from django.conf import settings

from .models import WordType,WordToken,Dialog,SegmentType,SegmentToken,Speaker,Category,Underlying
from .helper import fetch_buckeye_resource,fetch_media_resource,loadFile

logger = get_task_logger(__name__)

@task()
def loadSegments():
    logger.info("Loading segments...")
    segs = loadFile(fetch_buckeye_resource("SegmentInfo.txt"))
    ss = []
    for s in segs:
        ss.append(SegmentType(Label=s['Label'],Syllabic=bool(int(s['Syllabic'])),Obstruent=bool(int(s['Obstruent'])),Nasal=bool(int(s['Nasal'])),Vowel=bool(int(s['Vowel']))))
    SegmentType.objects.bulk_create(ss)
    logger.info("Loaded segments!")

@task()
def loadSpeakers():
    logger.info("Loading speakers...")
    speakers = loadFile(fetch_buckeye_resource("SpeakerInfo.txt"))
    ss = []
    for s in speakers:
        ss.append(Speaker(Number=s['Number'],Age=s['Age'],Gender=s['Gender'],NumFormants=s['NFormants'],Ceiling=s['Ceiling']))
    Speaker.objects.bulk_create(ss)
    logger.info("Loaded speakers!")

@task()
def loadCategories():
    logger.info("Loading categories...")
    cats = loadFile(fetch_buckeye_resource("CategoryInfo.txt"))
    cs = []
    for s in cats:
        cs.append(Category(Label=s['Label'],Description=s['Description'],CategoryType=s['Type']))
    Category.objects.bulk_create(cs)
    logger.info("Loaded categories!")


@task()
def load_base():
    job = TaskSet(tasks = [loadSegments.subtask(),
                            loadCategories.subtask(),
                            loadSpeakers.subtask(),])


@task()
def load_dialogs():
    sp = Speaker.objects.all()
    for s in sp:
        s.load_dialogs()

@task()
def doReset(logfilename):
    call_command('reset','buckeyebrowser', interactive=False,verbosity=0)
    res = chord((load_base.s()), load_dialogs.s())()
    res.get()

@task()
def combineResults(allout,wanted=None):
    if not os.path.isdir(fetch_media_resource("Results/Buckeye")):
        os.mkdir(fetch_media_resource("Results/Buckeye"))
    if wanted is None:
        head = allout[0][0].keys()
    else:
        head = wanted
    with open(fetch_media_resource("Results/Buckeye/analysis.txt"),'w') as f:
        f.write("\t".join(head))
        f.write("\n")
        for l in allout:
            for line in l:
                f.write("\t".join([ str(line[x]) for x in head]))
                f.write("\n")

@task()
def AnalyzeSpeaker(speaker,form):
    logger.info("Begin analysis of %s" % str(speaker))
    logger.info("Process %s" % str(os.getpid()))
    out = speaker.analyze(form)
    logger.info("Got %s lines for %s" % (str(len(out)),str(speaker)))
    with open(fetch_media_resource("Results/Buckeye/"+str(speaker)+".txt"),'w') as f:
        f.write("\t".join(out[0].keys()))
        f.write("\n")
        for l in out:
            f.write("\t".join(map(str,l.values())))
            f.write("\n")
    logger.info("Completed analysis of %s" % str(speaker))
    return out

@task()
def doBasicAnalysis(form):
    sp = [x for x in Speaker.objects.all() if str(x) != 's35']
    if settings.DEBUG:
        sp = Speaker.objects.filter(Number = 's03')
        out = AnalyzeSpeaker.delay(sp[0],form)
    else:
        #for s in sp:
        #    AnalyzeSpeaker.delay(s,form)
        #job = group([AnalyzeSpeaker.s(speaker, form) for speaker in sp])
        #job.apply_async(link=consolidateResultFiles.s())
        res = chord((AnalyzeSpeaker.s(s, form) for s in sp), combineResults.s(wanted=form.get_wanted_fields()))()

@task()
def consolidateResultFiles():
    outs = os.listdir(fetch_buckeye_resource("Results/Buckeye"))
    head = False
    with open(fetch_buckeye_resource("Results/Buckeye/allresults.txt"),'w') as allout:
        for fn in outs:
            with open(fetch_buckeye_resource("Results/Buckeye/%s"%fn),'r') as f:
                curhead = False
                for l in f:
                    if not head:
                        head = True
                    elif not curhead:
                        curhead = True
                        continue
                    allout.write(l)
