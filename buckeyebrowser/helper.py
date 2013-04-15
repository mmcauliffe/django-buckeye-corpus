import re
import os

from django.conf import settings


FILLERS = set(['uh','um','okay','yes','yeah','oh','heh','yknow','um-huh','uh-uh','uh-huh','uh-hum','mm-hmm'])


def fetch_buckeye_resource(uri):
    path = os.path.join(settings.BUCKEYE_ROOT,uri)
    return path

def fetch_media_resource(uri):
    path = os.path.join(settings.MEDIA_ROOT,uri)
    return path

def loadFile(path,cols=None):
    head = None
    with open(path,'r') as f:
        lines = []
        for l in f:
            if head is None:
                head = l.strip().split("\t")
                continue
            line = l.strip().split("\t")
            newline = { h: line[i] for i,h in enumerate(head) if cols is None or h in cols}
            lines.append(newline)
    return lines

def getphonerange(phones,begin,end):
    begin = begin-0.100
    end = end+0.100
    phonerange = []
    for i in xrange(len(phones)):
        if phones[i]['Begin'] < begin:
            continue
        elif phones[i]['End'] > end:
            break
        phonerange.append(phones[i])
    return phonerange

def loadPhones(path):
    with open(path,'r') as file_handle:
        f = re.split("#\r{0,1}\n",file_handle)[1]
        flist = f.splitlines()
        phones =[]
        begin = 0.0
        for l in flist:
            line = re.split("\s+\d{3}\s+",l.strip())
            if line[1].islower():
                end = float(phonlist[i][0])
                phones.append({'Label':phonlist[i][1],'Begin':begin,'End':end})
            begin = end
    return phones

def loadWords(path):
    with open(path,'r') as file_handle:
        f = re.split("#\r{0,1}\n",file_handle)[1]
        words = []
        begin = 0.0
        flist = f.splitlines()
        for l in flist:
            line = re.split("; | \d{3} ",l.strip())
            end = float(line[0])
            word = line[1]
            if word[0] != "<" and word[0] != "{":
                citation = re.sub(" ",";",line[2])
                phonetic = re.sub(" ",";",line[3])
                category = line[4]
            else:
                citation = "NULL"
                phonetic = "NULL"
                if word.startswith("<VOCNOISE") or word.startswith("<NOISE"):
                    category = "NOI"
                elif word.startswith("<LAUGH"):
                    category = "LAU"
                elif word.startswith("<SIL"):
                    category = "SIL"
                elif word.startswith("<EXT") or word.startswith("<HES") or word.startswith("<CUTOFF") or word.startswith("<ERROR"):
                    category = "ERR"
                else:
                    category = "OTH"
            if word in FILLERS:
                category = 'UH'
            line = {'Word':word,'Begin':begin,'End':end,'UR':citation,'SR':phonetic,'Category':category}
            words.append(line)
            begin = line['End']
    return words


def reorganize(path,name):
    words = loadWords(os.path.join(path,name+'.words'))
    phones = loadPhones(os.path.join(path,name+".phones"))
    wts = []
    for word in words:
        if word['UR'] != 'NULL':
            phonerange = getphonerange(phones,word['Begin'],word['End'])
            phonlist = word['SR'].split(";")
            justphones = []
            for j in xrange(len(phonerange)):
                phonerange[j]['Label'] = re.split(" {0,1};| {0,1}\+",phonerange[j]['Label'])[0]
                justphones.append(phonerange[j]['Label'])
            if len(phonerange) > len(phonlist):
                for i in xrange(len(phonerange)-len(phonlist)+1):
                    if justphones[i:i+len(phonlist)] == phonlist:
                        start = i
                        break
            elif len(phonerange) == len(phonlist):
                start = 0
            phonerange = phonerange[start:start+len(phonlist)]
            word['phonerange'] = phonerange
    return words

mysql_ur_string_lookup = """(SELECT GROUP_CONCAT(buckeyebrowser_segmenttype.Label SEPARATOR ' ')
                                FROM buckeyebrowser_underlying
                                INNER JOIN buckeyebrowser_segmenttype
                                ON buckeyebrowser_segmenttype.id
                                    = buckeyebrowser_underlying.SegmentType_id
                                WHERE buckeyebrowser_underlying.WordType_id
                                    =buckeyebrowser_wordtype.id) REGEXP %s"""

pg_ur_string_lookup = """array_to_string
                                        (
                                        ARRAY (
                                                SELECT st."Label"
                                                FROM buckeyebrowser_underlying ur, buckeyebrowser_segmenttype st
                                                WHERE st.id = ur."SegmentType_id"
                                                AND ur."WordType_id" = buckeyebrowser_wordtype.id
                                                ),
                                        ' '
                                        ) ~ %s"""

pg_speaker_center = """Select avg(AvgF1), avg(AvgF2) FROM (SELECT "StressVowel" as Vowel,
                        avg("StrVowelF1") as AvgF1,
                        avg("StrVowelF2") as AvgF2
                        FROM buckeyebrowser_wordtoken wtt
                        Inner join buckeyebrowser_wordtype wt
                        ON wt.id =wtt."WordType_id"
                        Inner join buckeyebrowser_dialog d
                        ON d.id = wtt."Dialog_id"
                        Inner join buckeyebrowser_speaker s
                        ON s.id = d."Speaker_id"
                        WHERE "CVSkel" = 'CVC'
                        AND d."Speaker_id" = %s
                        Group by "StressVowel") AS averages"""

mysql_speaker_center = """Select avg(AvgF1), avg(AvgF2) FROM (SELECT StressVowel as Vowel,
                        avg(StrVowelF1) as AvgF1,
                        avg(StrVowelF2) as AvgF2
                         FROM buckeyebrowser_wordtoken
                        Inner join buckeyebrowser_wordtype
                        ON buckeyebrowser_wordtype.id =buckeyebrowser_wordtoken.WordType_id
                        Inner join buckeyebrowser_dialog
                        ON buckeyebrowser_dialog.id = buckeyebrowser_wordtoken.Dialog_id
                        Inner join buckeyebrowser_speaker
                        ON buckeyebrowser_speaker.id = buckeyebrowser_dialog.Speaker_id
                        WHERE CVSkel = 'CVC'
                        AND buckeyebrowser_dialog.Speaker_id = %s
                        Group by StressVowel) AS averages"""
