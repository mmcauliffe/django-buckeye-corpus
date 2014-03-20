'''
Created on 2012-08-23

@author: michael
'''
import os,sys,re
import pickle
from datetime import datetime
from collections import Counter
import csv
import json

import networkx as nx
import numpy as np

from django.conf import settings
from django.db import connection

from django.core.management import call_command

from linghelper.phonetics.similarity.envelope import envelope_similarity,calc_envelope,envelope_match
from linghelper.phonetics.vowels import  extract_vowel

from .models import Speaker,Category,SegmentType,FollCondProbs,PrevCondProbs,SegmentToken,Underlying,WordToken,WordType,Dialog,BAD_WORDS,GOOD_WORDS

from .helper import (fetch_temp_resource, fetch_buckeye_resource,fetch_media_resource,
                    loadFile,reorganize2,load_phones,load_words,get_expected_phones)

def get_dist():
    cursor = connection.cursor()
    cursor.execute("""SELECT StressVowel as Vowel,buckeyebrowser_speaker.Number as Speaker,
                        avg(StrVowelF1) as AvgF1,std(StrVowelF1) as SDF1,
                        avg(StrVowelF2) as AvgF2, std(StrVowelF2) as SDF2
                         FROM buckeyebrowser_wordtoken
                        Inner join buckeyebrowser_wordtype
                        ON buckeyebrowser_wordtype.id =buckeyebrowser_wordtoken.WordType_id
                        Inner join buckeyebrowser_dialog
                        ON buckeyebrowser_dialog.id = buckeyebrowser_wordtoken.Dialog_id
                        Inner join buckeyebrowser_speaker
                        ON buckeyebrowser_speaker.id = buckeyebrowser_dialog.Speaker_id
                        WHERE CVSkel = 'CVC'
                        Group by StressVowel,buckeyebrowser_speaker.Number""")
    rows = cursor.fetchall()
    dist = {}
    for r in rows:
        if r[2] is not None:
            dist[(r[1],r[0])] = {'AvgF1':float(r[2]),
                                           'SDF1':float(r[3]),
                                           'AvgF2':float(r[4]),
                                           'SDF2':float(r[5])}
    return dist


def get_outliers(filename):
    dist = get_dist()
    outs = loadFile(os.path.join(fetch_media_resource('Results'),'Buckeye',filename),cols=['Token','Word','Speaker','Vowel','F1','F2'])
    outliers = []
    for o in outs:
        #o['Token'] = int(o['Token'])
        d = dist[(o['Speaker'],o['Vowel'])]
        if o['F1'] == 'None':
            outliers.append(o)
            continue
        if o['F2'] == 'None':
            outliers.append(o)
            continue
        reason = ''
        if float(o['F1']) > (d['AvgF1'] + (2.5 * d['SDF1'])) or float(o['F1']) < d['AvgF1'] - (2.5 * d['SDF1']):
            reason += 'F1'
        if float(o['F2']) > (d['AvgF2'] + (2.5 * d['SDF2'])) or float(o['F2']) < d['AvgF2'] - (2.5 * d['SDF2']):
            reason += '/F2'
        if reason != '':
            o['OutlierReason'] = reason
            outliers.append(o)
    return outliers

def load_segments_from_file():
    segs = loadFile(fetch_buckeye_resource("SegmentInfo.txt"))
    ss = []
    for s in segs:
        ss.append(SegmentType(Label=s['Label'],Syllabic=bool(int(s['Syllabic'])),Obstruent=bool(int(s['Obstruent'])),Nasal=bool(int(s['Nasal'])),Vowel=bool(int(s['Vowel']))))
    SegmentType.objects.bulk_create(ss)

def load_speakers_from_file():
    speakers = loadFile(fetch_buckeye_resource("SpeakerInfo.txt"))
    ss = []
    for s in speakers:
        ss.append(Speaker(Number=s['Number'],Age=s['Age'],Gender=s['Gender'],NumFormants=s['NFormants'],Ceiling=s['Ceiling']))
    Speaker.objects.bulk_create(ss)

def load_categories_from_file():
    cats = loadFile(fetch_buckeye_resource("CategoryInfo.txt"))
    cs = []
    for s in cats:
        cs.append(Category(Label=s['Label'],Description=s['Description'],CategoryType=s['Type']))
    Category.objects.bulk_create(cs)

def reset_database(speaker=None):
    if speaker is None:
        FollCondProbs.objects.all().delete()
        PrevCondProbs.objects.all().delete()
        SegmentToken.objects.all().delete()
        Underlying.objects.all().delete()

        WordToken.objects.all().delete()
        WordType.objects.all().delete()

        Dialog.objects.all().delete()

        Category.objects.all().delete()
        SegmentType.objects.all().delete()
        Speaker.objects.all().delete()
    else:
        s = Speaker.objects.get(Number=speaker)
        SegmentToken.objects.filter(WordToken__Dialog__Speaker = s).delete()
        WordToken.objects.filter(Dialog__Speaker = s).delete()

def load_basic_objects():
    load_segments_from_file()
    print('loaded segments')
    load_speakers_from_file()
    print('loaded speakers')
    load_categories_from_file()
    print('loaded categories')
    speakers = Speaker.objects.all().order_by('pk')
    for s in speakers:
        s.create_dialogs()
    print('loaded dialogs')


def load_database(test=False,speaker=None):
    speakers = Speaker.objects.all().order_by('pk')
    if speaker is not None:
        spk = Speaker.objects.get(Number = Speaker).pk
        speakers = speakers.filter(pk__gte = spk)
    if test:
        speakers = speakers.first()
        speakers.load_dialogs()
    else:
        for s in speakers:
            print('loading... '+str(s))
            start = datetime.now()
            print('Begin at ',str(start))
            s.load_dialogs()
            end = datetime.now()
            print('Finished at ',str(end))

def reload(speaker = None):
    reset_database(speaker=speaker)
    load_database(speaker=speaker)

def test_min():
    from linghelper.dtw import minEditDist
    t = ['k','ay']
    s = ['ow','k','ey']
    print(minEditDist(t,s))

def analyze_vowels():
    s = Speaker.objects.first()
    s.measure_vowels()
    #wt = WordType.objects.filter(Label = 'back').first()
    #print(wt.get_UR(stressed=True))
    #w = WordToken.objects.filter(WordType__Label = 'back').first()
    #print(w.get_stressed_vowel_info())
    #w.set_stress_formants()
    #print(w.AcousticInformation)

def test_reorg():
    s = Speaker.objects.get(Number='s09')
    name = 's0903a'
    reorganize2(s.get_path(),name)

def phone_match(one,two):
    if one != two \
                        and one not in two:
        return False
    return True

def validate_file_alignment():
    ds = Dialog.objects.all()
    for d in ds:
        wf = d.get_word_files()
        path = d.Speaker.get_path()
        for f in wf:
            name = re.sub(".words","",f)
            words = load_words(os.path.join(path,name+'.words'))
            phones = load_phones(os.path.join(path,name+".phones"))
            expected_phones = get_expected_phones(words)
            #for i in range(len(expected_phones)):
            #    if 'IVER' in expected_phones[i]:
            #        expected_phones[i] = 'IVER'
            expected_phones = list(filter(lambda x: '-' not in x,expected_phones))
            print(len(phones))
            print(len(expected_phones))
            print(name)
            not_found = []
            for i in range(len(expected_phones)):
                if not phone_match(phones[i]['Label'],expected_phones[i]):
                    count = 0
                    while not phone_match(phones[i]['Label'],expected_phones[i]):
                        not_found.append(phones.pop(i))
                        count += 1
                        if count > 30 or len(expected_phones) > len(phones):
                            print(name)
                            print(phones[i],expected_phones[i])
                            print(len(expected_phones),len(phones))
                            print(i)
                            print(expected_phones[i-4:i+4])
                            raise(Exception)

            print(len(not_found))

def validate_file_times():
    ds = Dialog.objects.all()
    for d in ds:
        wf = d.get_word_files()
        path = d.Speaker.get_path()
        for f in wf:
            name = re.sub(".words","",f)
            print(name)
            words = load_words(os.path.join(path,name+'.words'))
            phones = load_phones(os.path.join(path,name+".phones"))
            for w in words:
                if w['UR'] == 'NULL':
                    continue
                expected = w['SR'].split(';')
                beg = w['Begin']
                end = w['End']
                found = []
                while len(found) < len(expected):
                    cur_phone = phones.pop(0)
                    if phone_match(cur_phone['Label'],expected[len(found)]) \
                        and cur_phone['End'] >= beg and cur_phone['Begin'] <= end:
                            found.append(cur_phone)
                    if not len(phones):
                        print(name)
                        print(w)
                        raise(Exception)

def files_to_data(path,name):
    words = load_words(os.path.join(path,name+'.words'))
    phones = load_phones(os.path.join(path,name+".phones"))
    for i, w in enumerate(words):
        if w['UR'] == 'NULL':
            continue
        expected = w['SR'].split(';')
        beg = w['Begin']
        end = w['End']
        found = []
        while len(found) < len(expected):
            cur_phone = phones.pop(0)
            if phone_match(cur_phone['Label'],expected[len(found)]) \
                and cur_phone['End'] >= beg and cur_phone['Begin'] <= end:
                    found.append(cur_phone)
            if not len(phones):
                print(name)
                print(w)
                raise(Exception)
        words[i]['Phones'] = found
        words[i]['Begin'] = found[0]['Begin']
        words[i]['End'] = found[-1]['End']
    return words

def validate_data(words,name):
    for i, w in enumerate(words):
        if i > 0:
            prev = words[i-1]
            if prev['End'] > w['Begin']:
                if w['UR'] != 'NULL':
                    if prev['UR'] != 'NULL':
                        print(name)
                        print(prev)
                        print(w)
                        raise(Exception)
                else:
                    words[i]['Begin'] = prev['End']


        if i < len(words)-1:
            foll = words[i+1]
            if foll['Begin'] < w['End']:
                if w['UR'] != 'NULL':
                    if foll['UR'] != 'NULL':
                        print(name)
                        print(foll)
                        print(w)
                        raise(Exception)
                else:
                    words[i]['End'] = foll['Begin']
        try:
            cat = Category.objects.get(Label=w['Category'])
        except Exception:
            print(name)
            print(foll)
            print(w)

            raise(Exception)
    return words

def save_processed_file(data,path):
    filepath = os.path.join(fetch_buckeye_resource('Processed'),path)
    pickle.dump(data,open(filepath,'wb'))


def create_data_from_files():
    ds = Dialog.objects.all()
    for d in ds:
        wf = d.get_word_files()
        path = d.Speaker.get_path()
        for f in wf:
            name = re.sub(".words","",f)
            print(name)
            words = files_to_data(path,name)
            #words = validate_data(words,name)
            save_processed_file(words,name +'.txt')

def content_words():
    words = WordToken.objects.select_related('WordType','Category')
    words = words.prefetch_related('segmenttoken_set')
    words = words.filter(WordType__Label__regex = r'^[^{<]')
    words = words.filter(Category__CategoryType = 'Content').order_by('pk')
    return words

def get_distributions():
    wt = content_words()
    dist = Counter()
    for w in wt:
        vow,foll_seg,prec_seg,beg,end = w.get_stressed_vowel_info(word_internal=True)
        dist.update([(prec_seg,vow,foll_seg)])
    return dist
    #with open(,'w') as f:
        #writer = csv.writer(f)
        #for k,v in dist.items():

def convert_tokens_to_graph(s):
    print('%s' % (s))
    filepath = os.path.join(fetch_buckeye_resource('Graphs'),'%s.txt' % (str(s),))
    if os.path.isfile(filepath):
        return None
    g = nx.Graph()
    tokens = WordToken.objects.select_related('WordType','Dialog__Speaker','Category').filter(Dialog__Speaker = s)
    #tokens = tokens.exclude(Category__CategoryType__in = ['Pause','Disfluency','Other'])
    tokens = tokens.filter(WordType__Label__in = GOOD_WORDS)
    print(len(tokens))
    if len(tokens) == 0:
        return None
    g.add_nodes_from([(x.pk,{'Word':x.WordType.Label,
                            'Frequency':x.WordType.get_frequency(),
                            'ND': x.WordType.get_ND(),
                            'DialogPlace':x.get_dialog_place(),
                            'Duration':x.get_duration(),
                            'Speaker':str(s),
                            'SpeakerGender':s.Gender,
                            'SpeakerAge': s.Age,
                            'PrevSpeakRate' :x.get_previous_speaking_rate(),
                            'FollSpeakRate' : x.get_following_speaking_rate(),
                            'AvgSpeakRate' : s.get_avg_speaking_rate(),
                            'PrevCondProb' : x.get_previous_cond_prob(),
                            'FollCondProb' : x.get_following_cond_prob(),
                            'Repetitions' : x.get_repetitions(),
                            'wasRepeatedRecently' : x.get_recent_repetition(),
                            'OrthoLength' : len(x.WordType.Label),
                            'PhonoLength': x.WordType.UR.count(),
                            }) for x in tokens if x.is_acceptable()])
    for i in range(len(tokens)):
        envone = tokens[i].get_envelope()
        for j in range(i+1,len(tokens)):
            envtwo = tokens[j].get_envelope()
            sim = envelope_match(envone,envtwo)
            g.add_edge(tokens[i].pk,tokens[j].pk,weight = sim)
        path = fetch_temp_resource('buckeye-wt-%d.wav' % tokens[i].pk)
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
    pickle.dump(g,open(filepath,'wb'))

def token_to_env(wt):
    path = fetch_temp_resource('buckeye-wt-%d.wav' % wt.pk)
    if not os.path.isfile(path):
        extract_vowel(wt.get_dialog_path(),wt.Begin,wt.End,path)
    env = calc_envelope(path)
    return env

def token_envelope_similarity(wt1, wt2):
    wt1_path = fetch_temp_resource('buckeye-wt-%d.wav' % wt1.pk)
    if not os.path.isfile(wt1_path):
        extract_vowel(wt1.get_dialog_path(),wt1.Begin,wt1.End,wt1_path)
    wt2_path = fetch_temp_resource('buckeye-wt-%d.wav' % wt2.pk)
    if not os.path.isfile(wt2_path):
        extract_vowel(wt2.get_dialog_path(),wt2.Begin,wt2.End,wt2_path)
    sim = envelope_similarity(wt1_path,wt2_path)
    return sim

def my_node_link_data(G):
    data = {}
    data['nodes'] = [ dict(id=n, **G.node[n]) for n in G ]
    data['links'] = [dict(source=u,target=v, **d) for u,v,d in G.edges(data=True)]
    return data

def jsonize_graph():
    from networkx.readwrite import json_graph
    d = 's2902a'
    path = os.path.join(fetch_buckeye_resource('Graphs'),'%s.txt'% d)
    g = pickle.load(open(path,'rb'))
    newg = nx.Graph()
    for n in g.nodes_iter():
        newg.add_node(n.pk,name=n.WordType.Label,category=n.Category.Label,time=n.Begin)
    for e in g.edges_iter(data=True):
        newg.add_edge(e[0].pk,e[1].pk,weight=e[2]['weight'])
    data = my_node_link_data(newg)
    f = '/home/michael/dev/Linguistics/interactive_network/data/%s.json' % d
    json.dump(data,open(f,'w'),indent=4)

def gmlize_graph():
    from networkx.readwrite.gml import write_gml
    d = 's2902a'
    path = os.path.join(fetch_buckeye_resource('Graphs'),'%s.txt'% d)
    g = pickle.load(open(path,'rb'))
    newg = nx.Graph()
    for n in g.nodes_iter():
        newg.add_node(n.pk,name=n.WordType.Label,category=n.Category.Label,time=n.Begin)
    for e in g.edges_iter(data=True):
        newg.add_edge(e[0].pk,e[1].pk,weight=e[2]['weight'])
    f = '/home/michael/dev/Linguistics/interactive_network/data/%s.gml' % d
    write_gml(newg,f)

def get_graph_metrics():
    graphs = os.listdir(fetch_buckeye_resource('Graphs'))
    output = [['Speaker','Dialog','DialogPart','ClustCoeff','NTokens']]
    for f in graphs:
        print(f)
        path = os.path.join(fetch_buckeye_resource('Graphs'),f)
        name = f.split('.')[0]
        s = name[0:3]
        d = name[3:5]
        p = name[-1]
        g = pickle.load(open(path,'rb'))
        acc = nx.average_clustering(g,weight = 'weight')
        n = nx.number_of_nodes(g)
        output.append([s,d,p,acc,n])
    return output

def analyze_words_in_graph(f):
    path = os.path.join(fetch_buckeye_resource('Graphs'),f)
    outpath = fetch_media_resource(f)
    if os.path.isfile(outpath):
        return None
    g = pickle.load(open(path,'rb'))
    name = f.split('.')[0]
    speaker = name[0:3]
    #acc = nx.average_clustering(g,weight = 'weight')
    header = None
    nodes = g.nodes_iter(data=True)
    while header is None:
        t = next(nodes)
        if t[1] != {}:
            header = list(t[1].keys()) + ['Cluster_coeff']#,'Network_average_clustering']
    #header = ['Speaker','SpeakerGender','SpeakerAge',
    #            'Dialog','DialogPlace','Word','Frequency',
    #            'ND','Duration','Cluster_coeff','Network_average_clustering']
    for e in g.edges_iter(data=True):
        if np.isnan(e[-1]['weight']):
            g[e[0]][e[1]]['weight'] = 0
    with open(outpath,'w',newline='') as f:
        writer = csv.DictWriter(f,header,delimiter='\t')
        writer.writeheader()
        for n in g.nodes_iter(data=True):
            d = n[1]
            if d == {}:
                continue
            cluster_coeff = nx.clustering(g,n[0],weight='weight')
            d['Cluster_coeff'] = cluster_coeff
            #d['Speaker'] = speaker
            #d['Network_average_clustering'] = acc
            try:
                writer.writerow(d)
            except ValueError:
                print(d)
                print(f)
                raise(ValueError)

def combine_outputs():
    outdir = fetch_media_resource('')
    files = os.listdir(outdir)
    output = []
    for f in files:
        inpath = os.path.join(outdir,f)
        if not os.path.isfile(inpath):
            continue
        with open(inpath, newline='') as filehandle:
            reader = csv.DictReader(filehandle,delimiter='\t')
            for line in reader:
                output.append(line)
    with open(os.path.join(outdir,'allout.txt'),'w',newline='') as f:
        writer = csv.DictWriter(f,list(output[0].keys()),delimiter='\t')
        writer.writeheader()
        for line in output:
            writer.writerow(line)

def get_extra_info(d):
    print(d)
    tokens = WordToken.objects.select_related('WordType','Dialog__Speaker','Category').filter(Dialog = d)
    tokens = tokens.filter(Category__CategoryType = 'Content')#.exclude(WordType__Label__in = BAD_WORDS)
    path = fetch_media_resource('%s_extra.txt' % str(d))
    print(len(tokens))
    output = []
    #for t in tokens:
    #    if not t
    with open(path,'w') as f:
        writer= csv.writer(f,delimiter='\t')
        for t in tokens:
            writer.writerow([t.pk,str(d.Speaker),str(d),t.WordType.Label,t.get_dialog_place(),
                            t.get_previous_speaking_rate(),t.get_following_speaking_rate(),
                           t.get_previous_cond_prob(),t.is_acceptable(),
                            t.get_following_cond_prob(),t.get_repetitions(),
                           t.get_recent_repetition()])

def combine_extra_outputs():
    outdir = fetch_media_resource('')
    files = os.listdir(outdir)
    output = []
    header = ['Token','Speaker','Dialog','Word','DialogPlace','PrevSpeakRate',
                'FollSpeakRate','PrevCondProb','IsAcceptable','FollCondProb',
                'Repetitions','Given']
    for f in files:
        if 'extra' not in f:
            continue
        inpath = os.path.join(outdir,f)
        if not os.path.isfile(inpath):
            continue
        with open(inpath,'r') as filehandle:
            for line in filehandle:
                output.append(line.split('\t'))
    with open(os.path.join(outdir,'allout.txt'),'w') as f:
        writer = csv.writer(f,delimiter='\t')
        writer.writerow(header)
        for line in output:
            writer.writerow(line)

def plot_graph():
    import matlabplot.pyplot as plt
