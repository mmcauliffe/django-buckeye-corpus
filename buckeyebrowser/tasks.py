'''
Created on 2012-08-24

@author: michael
'''
import os,re,math

from celery import task,chord
from celery.signals import task_success
from django.db.models import Q

from models import WordType,WordToken,Dialog,SegmentType,SegmentToken,Speaker,Category,Underlying
from funcs import fetch_media_resource,loadFile

from LingToolsWebsite.functions import createlogfile,updatelogfile,resetApp


Fillers = set(['uh','um','okay','yes','yeah','oh','heh','yknow','um-huh','uh-uh','uh-huh','uh-hum','mm-hmm'])

#def doProbs(logfilename):
#    dialogs = Dialog.objects.all()
#    prevs = {}
#    folls = {}
#    for d in dialogs:
#        updatelogfile(logfilename,str(d))
#        words = WordToken.objects.filter(Dialog=d).order_by('DialogPart','Begin')
#        for w in words:
#            prev = w.getPreviousWord()
#            foll = w.getFollowingWord()
#            if prev is not None and prev.WordType.isWord():
#                if (w.WordType.pk,prev.WordType.pk) in prevs:
#                    prevs[(w.WordType.pk,prev.WordType.pk)] += 1
#                else:
#                    prevs[(w.WordType.pk,prev.WordType.pk)] = 1
#            if foll is not None and foll.WordType.isWord():
#                if (w.WordType.pk,foll.WordType.pk) in folls:
#                    prevs[(w.WordType.pk,foll.WordType.pk)] += 1
#                else:
#                    prevs[(w.WordType.pk,foll.WordType.pk)] = 1
#    pcInd = PrevCondProbs.objects.order_by('-pk')[:5]
#    if len(pcInd) > 0:
#        pcInd = pcInd[0].pk
#    else:
#        pcInd = 0
#    prevLines = []
#    for pc in prevs:
#        pcInd += 1
#        prev = WordType.objects.get(id=pc[1])
#        prevLines.append([pcInd,pc[0],pc[1],prevs[pc],float(prevs[pc])/float(prev.Count)])
#    updatelogfile(logfilename, 'Calculated Probabilities for Previous')
#    del prevs
#    fcInd = FollCondProbs.objects.order_by('-pk')[:5]
#    if len(fcInd) > 0:
#        fcInd = fcInd[0].pk
#    else:
#        fcInd = 0
#    follLines = []
#    for fc in folls:
#        fcInd += 1
#        foll = WordType.objects.get(id=fc.FollowingWord)
#        follLines.append([fcInd,fc[0],fc[1],folls[fc],float(prevs[fc])/float(foll.Count)])
#    updatelogfile(logfilename, 'Calculated Probabilities for Following')
#    del folls
#    PrevCondProbs.objects.create_in_bulk(prevLines)
#    updatelogfile(logfilename, 'Created previouses')
#    FollCondProbs.objects.create_in_bulk(follLines)
#    updatelogfile(logfilename, 'Created followings')

#def doFreqs():
#    words = WordType.objects.all()
#    for w in words:
#        c = w.getCount()
#        t = w.getFreq()
        
#@task()
#def doProbStuff(logfilename):
#    createlogfile(logfilename)
#    doFreqs()
#    updatelogfile(logfilename,'Did frequencies')
#    doProbs(logfilename)

#def interpret

def loadSegments():
    segs = loadFile(fetch_media_resource("VIC/SegmentInfo.txt"))
    ss = []
    for s in segs:
        ss.append(SegmentType(Label=s['Label'],Syllabic=bool(int(s['Syllabic'])),Obstruent=bool(int(s['Obstruent'])),Nasal=bool(int(s['Nasal'])),Vowel=bool(int(s['Vowel']))))
    SegmentType.objects.bulk_create(ss)

def loadSpeakers():
    speakers = loadFile(fetch_media_resource("VIC/SpeakerInfo.txt"))
    ss = []
    for s in speakers:
        ss.append(Speaker(Number=s['Number'],Age=s['Age'],Gender=s['Gender'],NumFormants=s['NFormants'],Ceiling=s['Ceiling']))
    Speaker.objects.bulk_create(ss)
        
def loadCategories():
    cats = loadFile(fetch_media_resource("VIC/CategoryInfo.txt"))
    cs = []
    for s in cats:
        cs.append(Category(Label=s['Label'],Description=s['Description'],CategoryType=s['Type']))
    Category.objects.bulk_create(cs)



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
    f = open(path).read()
    f = re.split("#\r{0,1}\n",f)[1]
    phonlist = f.splitlines()
    phones =[]
    for i in xrange(len(phonlist)):
        phonlist[i] = re.split("\s+\d{3}\s+",phonlist[i].strip())
        if phonlist[i][1].islower():
            if i != 0:
                begin = float(phonlist[i-1][0])
            else:
                begin = float(0)
            end = float(phonlist[i][0])
            phones.append({'Label':phonlist[i][1],'Begin':begin,'End':end})
    return phones

def loadWords(path):
    f = open(path).read()
    f = re.split("#\r{0,1}\n",f)[1]
    wordlist = f.splitlines()
    words = []
    for l in xrange(len(wordlist)):
        wordlist[l] = re.split("; | \d{3} ",wordlist[l].strip())
        if l != 0:
            begin = float(wordlist[l-1][0])
        else:
            begin = float(0)
        end = float(wordlist[l][0])
        word = wordlist[l][1]
        if word[0] != "<" and word[0] != "{":
            citation = re.sub(" ",";",wordlist[l][2])
            phonetic = re.sub(" ",";",wordlist[l][3])
            category = wordlist[l][4]
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
        if word in Fillers:
            category = 'UH'
        line = {'Word':word,'Begin':begin,'End':end,'UR':citation,'SR':phonetic,'Category':category}
        words.append(line)
    return words
        

def reorganize(path,filename,dialog):
    vowels = set([x.Label for x in SegmentType.objects.filter(Vowel=True) ])
    name = re.sub(".words","",filename)
    words = loadWords(os.path.join(path,filename))
    phones = loadPhones(os.path.join(path,name+".phones"))
    wordInd = WordToken.objects.order_by('-pk')[:5]
    if len(wordInd) > 0:
        wordInd = wordInd[0].pk
    else:
        wordInd = 0
    segInd = SegmentToken.objects.order_by('-pk')[:5]
    if len(segInd) > 0:
        segInd = segInd[0].pk
    else:
        segInd = 0
    wts = []
    sts = []
    for word in words:
        wordInd += 1
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
        cat = Category.objects.get(Label=word['Category'])
        wordTypes = WordType.objects.filter(Label=word['Word'])
        ur = word['UR'].split(";")
        w = None
        if w is None and len(wordTypes) != 0:
            for wType in wordTypes:
                if wType.isWord() and wType.getUR() == word['UR']:
                    w = wType
                    break
                elif not wType.isWord():
                    w = wType
        if w is None:
            w = WordType.objects.create(Label=word['Word'],Count=0)
            if w.isWord():
                uls = []
                cv = ''
                for i in range(len(ur)):
                    sType = SegmentType.objects.get(Label=ur[i])
                    if sType.isVowel():
                        cv += 'V'
                    else:
                        cv += 'C'
                    uls.append(Underlying(WordType=w,SegmentType=sType,Ordering=i))
                if cv == 'CVC':
                    w.StressVowel = ur[1]
                    uls[-2].Stressed = 1
                w.CVSkel = cv
                w.save()
                Underlying.objects.bulk_create(uls)
        wts.append([wordInd,word['Begin'],word['End'],w.pk,cat.pk,dialog.pk,name[-1]])
        if w.isWord():
            for s in phonerange:
                segInd += 1
                sType = SegmentType.objects.get(Label=s['Label'])
                sts.append([segInd,wordInd,sType.pk,s['Begin'],s['End']])
    WordToken.objects.create_in_bulk(wts)
    SegmentToken.objects.create_in_bulk(sts)

def getDialogs(path):
    files= os.listdir(path)
    wordFiles =[]
    dialogs=[]
    for j in xrange(len(files)):
        dialogs.append(files[j][3:5])
    dialogs = sorted(set(dialogs))
    for k in xrange(len(dialogs)):
        wordRound = []
        for j in xrange(len(files)):
            if files[j][3:5] == dialogs[k]:
                if re.search("\.words$",files[j]) != None:
                    wordRound.append(files[j])
        wordRound = sorted(wordRound)
        wordFiles.append(wordRound)
    return dialogs,wordFiles

def loadDialogs():
    speakers = Speaker.objects.all()
    ds = []
    for s in speakers:
        files= os.listdir(fetch_media_resource("VIC/Speakers/"+unicode(s)))
        dialogs=[]
        for j in xrange(len(files)):
            dialogs.append(files[j][3:5])
        dialogs = sorted(set(dialogs))
        for d in dialogs:
            ds.append(Dialog(Speaker=s,Number=d))
    Dialog.objects.bulk_create(ds)

        
def processDialogs(logfilename):
    #last = getlastfile()
    dialogs = Dialog.objects.all()
    #check = 0
    for d in dialogs:
        path = fetch_media_resource("VIC/Speakers/"+unicode(d.Speaker))
        files= os.listdir(path) 
        wordFiles = []
        for f in files:
            if f[:5] == unicode(d):
                if re.search("\.words$",f) is not None:
                    wordFiles.append(f)
        for f in wordFiles:
            #if f == last:
            #    check = 1
            #if check == 1:
            updatelogfile(logfilename,f)
            reorganize(path,f,d)


@task()
def doReset(logfilename):
    resetApp('buckeye')
    createlogfile(logfilename)
    loadSegments()
    updatelogfile(logfilename,"Loaded Segments")
    loadCategories()
    updatelogfile(logfilename,"Loaded Categories")
    loadSpeakers()
    updatelogfile(logfilename,"Loaded Speakers")
    loadDialogs()
    updatelogfile(logfilename,"Loaded Dialogs")
    processDialogs(logfilename)
    
@task()
def combineResults(allout):
    f = open(fetch_media_resource("Results/Buckeye/analysis.txt"),'w')
    f.write("\t".join(allout[0][0].keys()))
    f.write("\n")
    for l in allout:
        for line in l:
            f.write("\t".join(map(str,line.values())))
            f.write("\n")
    f.close()

@task()
def AnalyzeSpeaker(baseqs,speakNum,form):
    words = baseqs.filter(Dialog__Speaker__Number = speakNum)
    cur = ''
    allout = []
    #updatelogfile(logfilename, str(len(words)))
    for w in words:
        if not w.isAcceptable():
            continue
        #if str(w.Dialog) == 's2003' or str(w.Dialog) =='s4001':
        #    continue
        if cur != str(w.Dialog):
            cur = str(w.Dialog)
            #updatelogfile(logfilename, cur)
        allout.extend(w.getAnalysisLines(form))
    return allout
    #addResults(allout,fetch_media_resource("Results/Buckeye/analysis_%s.txt"%speakNum))
    
    #updatelogfile(logfilename, "All done!")

@task()
def doBasicAnalysis(logfilename,form):
    goodWords = ['back', 'bad', 'badge', 'bag', 'ball', 'bar', 'bare', 'base', 'bash', 'bass', 'bat', 'bath', 'beach', 'bean', 'bear', 'beat',
                 'bed', 'beer', 'bell', 'berth', 'big', 'bike', 'bill', 'birth', 'bitch', 'bite', 'boat', 'bob', 'boil', 'bomb', 'book', 'boom', 'boon',
                 'boss', 'bought', 'bout', 'bowl', 'buck', 'bum', 'burn', 'bus', 'bush', 'cab', 'cad', 'cake', 'calf', 'call', 'came', 'cap',
                 'car', 'care', 'case', 'cash', 'cat', 'catch', 'caught', 'cave', 'cell', 'chain', 'chair', 'chat', 'cheap', 'cheat', 'check',
                 'cheer', 'cheese', 'chess', 'chick', 'chief', 'chill', 'choice', 'choose', 'chose', 'church', 'coach', 'code', 'coke',
                 'comb', 'come', 'cone', 'cook', 'cool', 'cop', 'cope', 'corps', 'couch', 'cough', 'cub', 'cuff', 'cup', 'curl', 'curve', 'cut',
                 'dab', 'dad', 'dare', 'date', 'dawn', 'dead', 'deal', 'dear', 'death', 'debt', 'deck', 'deed', 'deep', 'deer', 'dime', 'dirt',
                 'doc', 'dodge', 'dog', 'dole', 'doll', 'doom', 'door', 'dot', 'doubt', 'duck', 'dug', 'dumb', 'face', 'fad', 'fade', 'fail',
                 'fair', 'faith', 'fake', 'fall', 'fame', 'fan', 'far', 'fat', 'faze', 'fear', 'fed', 'feed', 'feet', 'fell', 'fight', 'file', 'fill', 'fine',
                 'firm', 'fish', 'fit', 'fog', 'folk', 'food', 'fool', 'foot', 'fore', 'fought', 'fun', 'fuss', 'gain', 'game', 'gap', 'gas',
                 'gate', 'gave', 'gear', 'geese', 'gig', 'girl', 'give', 'goal', 'gone', 'good', 'goose', 'gum', 'gun', 'gut', 'gym', 'hail', 'hair',
                 'hall', 'ham', 'hang', 'hash', 'hat', 'hate', 'head', 'hear', 'heard', 'heat', 'height', 'hick', 'hid', 'hide', 'hill', 'hip', 'hit',
                 'hole', 'home', 'hood', 'hook', 'hop', 'hope', 'hot', 'house', 'hug', 'hum', 'hung', 'hurt', 'jab', 'jail', 'jam', 'jazz', 'jerk',
                 'jet', 'job', 'jog', 'join', 'joke', 'judge', 'june', 'keep', 'kick', 'kid', 'kill', 'king', 'kiss', 'knife', 'knit', 'knob', 'knock',
                 'known', 'lack', 'lag', 'laid', 'lake', 'lame', 'lane', 'lash', 'latch', 'late', 'laugh', 'lawn', 'league', 'leak', 'lean', 'learn',
                 'lease', 'leash', 'leave', 'led', 'leg', 'let', 'lid', 'life', 'light', 'line', 'load', 'loan', 'lock', 'lodge', 'lone', 'long', 'look',
                 'loose', 'lose', 'loss', 'loud', 'love', 'loyal', 'luck', 'mad', 'made', 'maid', 'mail', 'main', 'make', 'male', 'mall',
                 'map', 'mass', 'mat', 'match', 'math', 'meal', 'meat', 'meet', 'men', 'mess', 'met', 'mid', 'mike', 'mile', 'mill',
                 'miss', 'mock', 'moon', 'mouth', 'move', 'mud', 'nail', 'name', 'nap', 'neat', 'neck', 'need', 'nerve', 'net', 'news',
                 'nice', 'niche', 'niece', 'night', 'noise', 'noon', 'nose', 'notch', 'note', 'noun', 'nurse', 'nut', 'pace', 'pack', 'page',
                 'paid', 'pain', 'pair', 'pal', 'pass', 'pat', 'path', 'pawn', 'peace', 'peak', 'pearl', 'peek', 'peer', 'pen', 'pet', 'phase',
                 'phone', 'pick', 'piece', 'pile', 'pill', 'pine', 'pipe', 'pit', 'pool', 'poor', 'pop', 'pope', 'pot', 'pour', 'puck', 'push',
                 'put', 'race', 'rage', 'rail', 'rain', 'raise', 'ran', 'rash', 'rat', 'rate', 'rave', 'reach', 'rear', 'red', 'reef', 'reel',
                 'rice', 'rich', 'ride', 'ring', 'rise', 'road', 'roam', 'rob', 'rock', 'rode', 'role', 'roll', 'roof', 'room', 'rose', 'rough',
                 'rub', 'rude', 'rule', 'run', 'rush', 'sack', 'sad', 'safe', 'said', 'sake', 'sale', 'sang', 'sat', 'save', 'scene', 'search',
                 'seat', 'seen', 'sell', 'serve', 'set', 'sewn', 'shake', 'shame', 'shape', 'share', 'shave', 'shed', 'sheep', 'sheer', 'sheet',
                 'shell', 'ship', 'shirt', 'shock', 'shoot', 'shop', 'shot', 'shown', 'shun', 'shut', 'sick', 'side', 'sight', 'sign', 'sin', 'sing',
                 'sit', 'site', 'size', 'soap', 'son', 'song', 'soon', 'soul', 'soup', 'south', 'suit', 'sung', 'tab', 'tag', 'tail', 'take', 'talk',
                 'tap', 'tape', 'taught', 'teach', 'team', 'tease', 'teeth', 'tell', 'term', 'theme', 'thick', 'thief', 'thing', 'thought', 'tiff',
                 'tight', 'time', 'tip', 'tongue', 'took', 'tool', 'top', 'tore', 'toss', 'touch', 'tough', 'tour', 'towel', 'town', 'tub', 'tube',
                 'tune', 'turn', 'type', 'use', 'van', 'vet', 'vice', 'voice', 'vote', 'wade', 'wage', 'wait', 'wake', 'walk', 'wall', 'war',
                 'wash', 'watch', 'wear', 'web', 'week', 'weight', 'wet', 'whack', 'wheat', 'wheel', 'whim', 'whine', 'whip', 'white',
                 'whole', 'wick', 'wide', 'wife', 'win', 'wine', 'wing', 'wise', 'wish', 'woke', 'womb', 'wood', 'word', 'wore', 'work',
                 'worse', 'wreck', 'wright', 'write', 'wrong', 'wrote', 'wrought', 'year', 'yell', 'young', 'youth', 'zip']
    #Remove: pull, full, bull, real
    vows = ['aa','ae','eh','ey','ih','iy','ow','uh','uw']
    #createlogfile(logfilename)
    words = WordToken.objects.all()
    words = words.filter(WordType__CVSkel='CVC')
    #words = words.filter(WordType__StressVowel__in = vows)
    words = words.filter(WordType__Label__in = goodWords).order_by('Dialog')
    sp = [str(x) for x in Speaker.objects.all() if str(x) != 's35']
    #for s in sp:
    #    AnalyzeSpeaker.delay(words, s,form)
    res = chord((AnalyzeSpeaker.s(words, s, form) for s in sp), combineResults.s())()
    res.get()
#@task_success.connect(sender=doBasicAnalysis)
#def consolidateResultFiles():
#    outs = os.listdir(fetch_media_resource("Results/Buckeye"))
#    os.remove(fetch_media_resource("Results/Buckeye/analysis.txt"))
#    head = False
#    allout = open(fetch_media_resource("Results/Buckeye/analysis.txt"),'w')
#    for fn in outs:
#        f = open(fetch_media_resource("Results/Buckeye/%s"%fn))
#        ls = f.read().splitlines()
#        if not head:
#            allout.write(ls[0]+"\n")
#        allout.write("\n".join(ls[1:]))
#        f.close()
#    allout.close()
        