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
from .utils import load_segments_from_file,load_speakers_from_file,load_categories_from_file

logger = get_task_logger(__name__)

@task()
def load_segments():
    logger.info("Loading segments...")
    load_segments_from_file()
    logger.info("Loaded segments!")

@task()
def load_speakers():
    logger.info("Loading speakers...")
    load_speakers_from_file()
    logger.info("Loaded speakers!")

@task()
def load_categories():
    logger.info("Loading categories...")
    load_categories_from_file()
    logger.info("Loaded categories!")


@task()
def load_speaker(speaker):
    logger.info("Begin loading of %s" % str(speaker))
    speaker.load_dialogs()
    logger.info("Completed loading of %s" % str(speaker))

@task()
def load_dialogs():
    sp = Speaker.objects.all()
    job = group(load_speaker.si(s) for s in sp)
    res = job()
    res.get()


@task()
def do_reset(logfilename):
    #call_command('reset','buckeyebrowser', interactive=False,verbosity=0)
    res = chord([load_segments.si(),
                            load_categories.si(),
                            load_speakers.si()])(load_dialogs.si())
    res.get()

@task()
def combine_results(allout,wanted=None):
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
def analyze_speaker(speaker,form):
    logger.info("Begin analysis of %s" % str(speaker))
    logger.info("Process %s" % str(os.getpid()))
    out = speaker.analyze(form)
    logger.info("Got %s lines for %s" % (str(len(out)),str(speaker)))
    wanted = form.get_wanted_fields()
    with open(fetch_media_resource("Results/Buckeye/"+str(speaker)+".txt"),'w') as f:
        f.write("\t".join(wanted))
        f.write("\n")
        for l in out:
            f.write("\t".join([ str(l[x]) for x in wanted]))
            f.write("\n")
    logger.info("Completed analysis of %s" % str(speaker))
    return out

@task()
def do_analysis(form):
    sp = [x for x in Speaker.objects.all() if str(x) != 's35']
    #if settings.DEBUG:
    #    sp = Speaker.objects.filter(Number = 's03')
    res = chord((analyze_speaker.s(s, form) for s in sp), combine_results.s(wanted=form.get_wanted_fields()))()

