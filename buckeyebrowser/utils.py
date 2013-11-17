'''
Created on 2012-08-23

@author: michael
'''
import os

from django.conf import settings

from .helper import fetch_buckeye_resource,fetch_media_resource,loadFile

def get_dist():
    from django.db import connection
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






