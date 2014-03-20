'''
Created on 2012-08-24

@author: michael
'''
import os
import re
import math
import pickle
import csv
import networkx as nx

from celery import task,chord,group
from celery.signals import task_success
from celery.utils.log import get_task_logger

from django.db.models import Q
from django.core.management import call_command
from django.conf import settings

from .models import WordType,WordToken,Dialog,SegmentType,SegmentToken,Speaker,Category,Underlying
from .helper import fetch_buckeye_resource,fetch_media_resource,loadFile
from .utils import load_segments_from_file,load_speakers_from_file,load_categories_from_file,convert_tokens_to_graph,analyze_words_in_graph,get_extra_info

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
def load_dialogs():
    sp = Speaker.objects.all()
    for s in sp:
        s.create_dialogs()

@task()
def load_wordtypes():
    ds = Dialog.objects.all()
    for d in ds:
        d.load_wordtypes()

@task()
def load_speaker_wordtokens(speaker):
    logger.info("Begin loading of %s" % str(speaker))
    speaker.load_wordtokens()
    logger.info("Completed loading of %s" % str(speaker))

@task()
def load_wordtokens():
    sp = Speaker.objects.all()
    job = group(load_speaker_wordtokens.si(s) for s in sp)
    res = job()

@task()
def measure_speaker_vowels(speaker):
    logger.info("Begin analysis of %s" % str(speaker))
    speaker.measure_vowels()
    logger.info("Completed analysis of %s" % str(speaker))

@task()
def remeasure_speaker_vowels(speaker):
    logger.info("Begin reanalysis of %s" % str(speaker))
    speaker.remeasure_vowels()
    logger.info("Completed reanalysis of %s" % str(speaker))

@task()
def do_vowel_measure():
    sp = Speaker.objects.all()
    job = group(measure_speaker_vowels.si(s) for s in sp)
    res = job()

@task()
def do_vowel_remeasure():
    sp = Speaker.objects.all()
    job = group(remeasure_speaker_vowels.si(s) for s in sp)
    res = job()


@task()
def do_all_acoustics():
    (do_vowel_measure.si() | do_vowel_remeasure.si()).apply_async()

@task()
def do_reset(basic = True):
    #call_command('reset','buckeyebrowser', interactive=False,verbosity=0)
    if basic:
        (load_segments.si() |
            load_categories.si() |
            load_speakers.si() |
            load_dialogs.si() |
            load_wordtypes.si() |
            load_wordtokens.si()
            ).apply_async()
    else:
        (
            load_wordtypes.si() |
            load_wordtokens.si()
            ).apply_async()
    #res = chord([load_segments.si(),
    #                        load_categories.si(),
    #                        load_speakers.si()])(load_dialogs.si())
    #res.get()

def do_word_token_check():
    load_wordtokens.apply_async()

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
def convert_to_graph(s):
    convert_tokens_to_graph(s)

@task()
def validate():
    ds = Dialog.objects.all()
    for d in ds:
        d.validate_wordtokens()

@task()
def do_graph_analysis():
    sp = Speaker.objects.all()
    job = group(convert_to_graph.si(s) for s in sp)
    res = job()

@task()
def get_clustering(f):
    path = os.path.join(fetch_buckeye_resource('Graphs'),f)
    outpath = fetch_media_resource(f)
    if os.path.isfile(outpath):
        return None
    name = f.split('.')[0]
    s = name[0:3]
    d = name[3:5]
    p = name[-1]
    g = pickle.load(open(path,'rb'))
    acc = nx.average_clustering(g,weight = 'weight')
    n = nx.number_of_nodes(g)
    with open(outpath,'w') as f:
        writer = csv.writer(f,delimiter='\t')
        writer.writerow([s,d,p,acc,n])

@task()
def write_clustering_output(out):
    from djcelery.picklefield import decode
    outpath = fetch_media_resource('graph_clustering.txt')
    with open(outpath,'w') as f:
        writer = csv.writer(f,delimiter='\t')
        writer.writerow(['Speaker','Dialog','DialogPart','ClusteringCoeff','NTokens'])
        for r in out:
            r = decode(r)
            writer.writerow(r)

@task()
def simplify(f):
    path = os.path.join(fetch_buckeye_resource('Graphs'),f)
    newpath = os.path.join(fetch_buckeye_resource('SimpleGraphs'),f)
    if os.path.isfile(newpath):
        return None
    g = pickle.load(open(path,'rb'))
    newg = nx.Graph()
    for n in g.nodes_iter():
        newg.add_node(n.pk,name=n.WordType.Label,category=n.Category.Label,time=n.Begin)
    for e in g.edges_iter(data=True):
        if e[2]['weight'] > 0.9:
            newg.add_edge(e[0].pk,e[1].pk)
    pickle.dump(newg,open(newpath,'wb'))

@task()
def simplify_graphs():
    graphs = os.listdir(fetch_buckeye_resource('Graphs'))
    job = group(simplify.si(f) for f in graphs)
    res = job()

@task()
def analyze_graph(f):
    analyze_words_in_graph(f)

@task()
def analyze_graphs():
    graphs = os.listdir(fetch_buckeye_resource('Graphs'))
    job = group(analyze_graph.si(f) for f in graphs)
    res = job()
    #res = chord(get_clustering.s(f) for f in graphs)(write_clustering_output.s()).get()

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
def fix_output(d):
    get_extra_info(d)

@task()
def fix_all_outputs():
    ds = Dialog.objects.all()
    job = group(fix_output.si(d) for d in ds)
    res = job()


@task()
def do_analysis(form):
    sp = [x for x in Speaker.objects.all() if str(x) != 's35']
    #if settings.DEBUG:
    #    sp = Speaker.objects.filter(Number = 's03')
    res = chord((analyze_speaker.s(s, form) for s in sp), combine_results.s(wanted=form.get_wanted_fields()))()

