
import os
import re
from PIL import Image
import math
import copy
from collections import OrderedDict

from django.db import models
from django.conf import settings
from django.db.models import Count,Sum,Q

from picklefield.fields import PickledObjectField
import caching.base

# Create your models here.


from linghelper import DTW,getSemanticRelatedness
from praatinterface import PraatLoader

if 'phonostats' in settings.INSTALLED_APPS:
    from phonostats.utils import getNeighCount,getPhonotacticProb,guessStress

if 'celex' in settings.INSTALLED_APPS:
    from celex.utils import categorize_words,get_lexical_info,lookupCat

if 'mysql' in settings.DATABASES['default']['ENGINE']:
    from .helper import mysql_ur_string_lookup as UR_LOOKUP
    from .helper import mysql_speaker_center as SPEAKER_SQL
else:
    from .helper import pg_ur_string_lookup as UR_LOOKUP
    from .helper import pg_speaker_center as SPEAKER_SQL

from .helper import fetch_buckeye_resource,reorganize
from .managers import BulkManager


GOOD_WORDS = ['back', 'bad', 'badge', 'bag', 'ball', 'bar', 'bare', 'base', 'bash', 'bass', 'bat', 'bath', 'beach', 'bean', 'bear', 'beat',
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
                 'loose', 'lose', 'loss', 'loud', 'love', 'luck', 'mad', 'made', 'maid', 'mail', 'main', 'make', 'male', 'mall',
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
                 'tight', 'time', 'tip', 'tongue', 'took', 'tool', 'top', 'tore', 'toss', 'touch', 'tough', 'tour', 'town', 'tub', 'tube',
                 'tune', 'turn', 'type', 'use', 'van', 'vet', 'vice', 'voice', 'vote', 'wade', 'wage', 'wait', 'wake', 'walk', 'wall', 'war',
                 'wash', 'watch', 'wear', 'web', 'week', 'weight', 'wet', 'whack', 'wheat', 'wheel', 'whim', 'whine', 'whip', 'white',
                 'whole', 'wick', 'wide', 'wife', 'win', 'wine', 'wing', 'wise', 'wish', 'woke', 'womb', 'wood', 'word', 'wore', 'work',
                 'worse', 'wreck', 'wright', 'write', 'wrong', 'wrote', 'wrought', 'year', 'yell', 'young', 'youth', 'zip']
    #Remove: pull, full, bull, real
MONOPHTHONGS = ['aa','ae','eh','ey','ih','iy','ow','uh','uw']

class WTManager(BulkManager):
    tbl_name = "buckeyebrowser_wordtoken"
    cols = ['id','Begin','End','WordType_id','Category_id','Dialog_id','DialogPart']

class STManager(BulkManager):
    tbl_name = "buckeyebrowser_segmenttoken"
    cols = ['id','WordToken_id','SegmentType_id','Begin','End']

class Speaker(caching.base.CachingMixin,models.Model):
    Number = models.CharField(max_length=3)
    Gender = models.CharField(max_length=10)
    Age = models.CharField(max_length=10)
    NumFormants = models.DecimalField('Number of formants',max_digits=4,decimal_places=1)
    Ceiling = models.IntegerField()
    F1center = models.FloatField(blank=True,null=True)
    F2center = models.FloatField(blank=True,null=True)
    AvgSpeakingRate = models.FloatField(blank=True,null=True)

    objects = caching.base.CachingManager()

    def __unicode__(self):
        return u'%s' % (self.Number,)

    def getAHCenter(self):
        if self.F1center is not None and self.F2center is not None:
            return (self.F1center,self.F2center)
        qs = WordToken.objects.filter(WordType__CVSkel='CVC').filter(WordType__StressVowel='ah').filter(Dialog__Speaker__pk=self.pk)
        totF1 = filter(lambda x: x is not None,[q.getStrF1() for q in qs])
        totF2 = filter(lambda x: x is not None,[q.getStrF2() for q in qs])
        self.F1center = sum(totF1)/float(len(qs))
        self.F2center = sum(totF2)/float(len(qs))
        self.save()
        return (self.F1center,self.F2center)

    def getCenter(self):
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute(SPEAKER_SQL,[self.pk])
        center = cursor.fetchone()
        return (center[0],center[1])

    def getAvgSpeakingRate(self):
        if self.AvgSpeakingRate is not None:
            return self.AvgSpeakingRate
        words = WordToken.objects.filter(Dialog__Speaker=self).filter(Category__CategoryType__in = ['Content','Function','Function_Content','Function_Function'])
        dur = sum([x.getDuration() for x in words])
        sylls = sum([x.isSyllabic() for y in words for x in y.SR.all() if x.isSyllabic()])
        self.AvgSpeakingRate = float(sylls)/float(dur)
        self.save()
        return self.AvgSpeakingRate

    def create_dialogs(self):
        files= os.listdir(fetch_buckeye_resource("Speakers/"+str(s)))
        dialogs = sorted(set([ f[3:5] for f in files]))
        Dialog.objects.bulk_create([ Dialog(Speaker=self,Number=d) for d in dialogs])

    def analyze(self,form):
        words = WordToken.objects.select_related('WordType','Dialog','Dialog__Speaker')
        words = words.filter(WordType__Label__regex = '^[^{<]').filter(Dialog__Speaker=self)
        #words = words.filter(WordType__CVSkel='CVC')
        #words = words.filter(WordType__Label__in = GOOD_WORDS)
        #words = words.filter(WordType__StressVowel__in = MONOPHTHONGS)
        allout = []
        print(str(self))
        print("\n")
        print(len(words))
        for w in words:
            if settings.DEBUG:
                print(w.pk)
            if not w.WordType.isAcceptable():
                continue
            if not w.isAcceptable():
                continue
            if str(w.Dialog) == 's2003' or str(w.Dialog) =='s4001':
                continue
            out = w.getAnalysisLines(form)
            if out is None:
                continue
            allout.extend(out)
            if settings.DEBUG:
                print allout[-1]
        return allout

    def load_dialogs(self):
        self.create_dialogs()
        for d in Dialog.objects.filter(Speaker = self):
            d.load_in()

    def get_path(self):
        return fetch_buckeye_resource("Speakers/"+unicode(self))




class Dialog(caching.base.CachingMixin,models.Model):
    Speaker = models.ForeignKey(Speaker)
    Number = models.CharField(max_length=10)

    objects = caching.base.CachingManager()

    def __unicode__(self):
        return u'%s%s' % (self.Speaker,self.Number)

    def get_word_files(self):
        files = os.listdir(self.Speaker.get_path())
        word_files = [f for f in files if f[:5] == str(d) and re.search("\.words$",f) is not None]
        return word_files

    def load_in(self):
        wf = self.get_word_files()
        for f in wf:
            name = re.sub(".words","",f)
            words = reorganize(self.Speaker.get_path(),name)
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
            wt =WordToken.objects.create(Begin=word['Begin'],End=word['End'],WordType=w,Category=cat,Dialog=self,DialogPart=name[-1])
            if w.isWord():
                sts = []
                for s in word['phonerange']:
                    sType = SegmentType.objects.get(Label=s['Label'])
                    sts.append(SegmentToken(WordToken=wt,SegmentType = sType,Begin=s['Begin'],End=s['End']))
                SegmentToken.objects.bulk_create(sts)



class SegmentType(caching.base.CachingMixin,models.Model):
    Label = models.CharField(max_length=10)
    Syllabic = models.BooleanField()
    Obstruent = models.BooleanField()
    Nasal = models.BooleanField()
    Vowel = models.BooleanField()

    objects = caching.base.CachingManager()

    def isSyllabic(self):
        return self.Syllabic

    def isNasal(self):
        return self.Nasal

    def isObs(self):
        return self.Obstruent

    def isVowel(self):
        return self.Vowel

    def __unicode__(self):
        return u'%s' % (self.Label,)

    def getAverageDur(self):
        qs = SegmentToken.objects.filter(SegmentType=self)
        durs = [x.End - x.Begin for x in qs]
        return sum(durs)/float(len(durs))

class Underlying(caching.base.CachingMixin,models.Model):
    WordType = models.ForeignKey('WordType')
    SegmentType = models.ForeignKey(SegmentType)
    Ordering = models.IntegerField()
    Stressed = models.IntegerField(blank=True,null=True)

    objects = caching.base.CachingManager()

    def getStrTrans(self):
        if self.Stressed is None:
            return str(self.SegmentType).upper()
        return str(self.SegmentType).upper()+str(self.Stressed)

    class Meta:
        ordering = ['Ordering']

class SegmentToken(caching.base.CachingMixin,models.Model):
    WordToken = models.ForeignKey('WordToken')
    SegmentType = models.ForeignKey(SegmentType)
    Begin = models.FloatField()
    End = models.FloatField()
    Stressed = models.NullBooleanField()

    objects = caching.base.CachingManager()

    def __unicode__(self):
        return u'%s' % unicode(self.SegmentType)

    class Meta:
        ordering = ['Begin']

    def getEnd(self):
        return self.End

class Category(caching.base.CachingMixin,models.Model):
    Label = models.CharField(max_length=10)
    Description = models.CharField(max_length=250)
    CategoryType = models.CharField('Category type',max_length=100)

    objects = caching.base.CachingManager()

    def isContent(self):
        if self.CategoryType == 'Content':
            return True
        return False

    def __unicode__(self):
        return u'%s' % self.Label

class PrevCondProbs(caching.base.CachingMixin,models.Model):
    ActWord = models.ForeignKey('WordType',related_name='prevactword')
    PreviousWord = models.ForeignKey('WordType',related_name='prevword')
    Count = models.IntegerField(blank=True,null=True)
    Prob = models.FloatField(blank=True,null=True)

    objects = caching.base.CachingManager()

    def getProb(self):
        if self.Prob is not None:
            return self.Prob
        qs = WordToken.objects.filter(WordType=self.ActWord)
        self.Count = 0
        for i in xrange(len(qs)):
            if qs[i].getPreviousWord().WordType == self.PreviousWord:
                self.Count += 1
        self.Prob = float(self.Count) / float(self.PreviousWord.getCount())
        self.save()
        return self.Prob

class FollCondProbs(caching.base.CachingMixin,models.Model):
    ActWord = models.ForeignKey('WordType',related_name='follactword')
    FollowingWord = models.ForeignKey('WordType',related_name='follword')
    Count = models.IntegerField(blank=True,null=True)
    Prob = models.FloatField(blank=True,null=True)

    objects = caching.base.CachingManager()

    def getProb(self):
        if self.Prob is not None:
            return self.Prob
        qs = WordToken.objects.filter(WordType=self.ActWord)
        self.Count = 0
        for i in xrange(len(qs)):
            if qs[i].getFollowingWord().WordType == self.FollowingWord:
                self.Count += 1
        self.Prob = float(self.Count) / float(self.FollowingWord.getCount())
        self.save()
        return self.Prob

class WordType(caching.base.CachingMixin,models.Model):
    Label = models.CharField(max_length=250)
    UR = models.ManyToManyField(SegmentType,through=Underlying)
    Count = models.IntegerField(blank=True,null=True)
    Frequency = models.FloatField(blank=True,null=True)
    FreqSource = models.CharField(max_length=100,blank=True,null=True)
    SPhonoProb = models.FloatField(blank=True,null=True)
    BiPhonoProb = models.FloatField(blank=True,null=True)
    ND = models.FloatField(blank=True,null=True)
    FWND = models.FloatField(blank=True,null=True)
    CVSkel = models.CharField(max_length=100,blank=True,null=True)
    StressVowel = models.CharField(max_length=10,blank=True,null=True)

    objects = caching.base.CachingManager()

    def __unicode__(self):
        return u'%s' % self.Label

    def isAcceptable(self):
        qs = self.wordtoken_set.filter(Output__isnull=False)
        if len(qs) > 0:
            if 'CelexCategory' in qs[0].Output and qs[0].Output['CelexCategory'] not in ['N','V','ADV','A']:
                return False
        return True

    def getUR(self,stressed=False,blick_style=False):
        t = ' '.join([s.getStrTrans() for s in self.underlying_set.all()])
        if not stressed:
            t = re.sub(r'\d',r'',t)
        if blick_style:
            t = re.sub(r'EL(\d?)',r'AH\1 L',t)
        return t

    def getBaseDuration(self):
        return sum([x.getAverageDur() for x in self.UR.all()])

    def getPhonoSource(self):
        if self.PhonoSource is None:
            return ''
        return self.PhonoSource

    def getStressVowel(self):
        if self.StressVowel is None:
            self.figureStresses()
        return self.StressVowel

    def figureStresses(self):
        guessed = guessStress(self.getUR(blick_style=True))
        stresses = re.sub(r'\D',r'',guessed)
        syls = self.underlying_set.filter(SegmentType__Syllabic=True)
        for i in range(len(syls)):
            syls[i].Stressed = int(stresses[i])
            syls[i].save()
            if syls[i].Stressed == 1:
                self.StressVowel = str(syls[i].SegmentType)
                self.save()



    def getCVSkel(self):
        if self.CVSkel is not None:
            return self.CVSkel
        cv = ''
        for seg in self.UR.all():
            if seg.isVowel():
                cv += 'V'
            else:
                cv += 'C'
        self.CVSkel = cv
        self.save()
        return self.CVSkel

    def getNumSylls(self):
        numSylls = 0
        for seg in self.UR.all():
            if seg.isSyllabic():
                numSylls += 1
        return numSylls

    def getNumVows(self):
        numVows = 0
        for seg in self.UR.all():
            if seg.isVowel():
                numVows += 1
        return numVows

    def isWord(self):
        if self.Label.startswith("{") or self.Label.startswith("<"):
            return False
        else:
            return True

    def getCount(self):
        if self.Count != 0:
            return self.Count
        self.Count = WordToken.objects.filter(WordType=self).count()
        self.save()
        return self.Count

    def getFreq(self,subset='all',speaker=None,dialog=None):
        if subset=='all' and self.Frequency is not None:
            return self.Frequency
        base = WordToken.objects.all().select_related('WordType','Category')
        if subset == 'gender' and speaker is not None:
            base = base.filter(Dialog__Speaker__Gender = speaker.Gender)
        elif subset == 'age' and speaker is not None:
            base = base.filter(Dialog__Speaker__Age = speaker.Age)
        elif subset == 'speaker' and speaker is not None:
            base = base.filter(Dialog__Speaker = speaker)
        elif subset == 'dialog' and dialog is not None:
            base = base.filter(Dialog = dialog)

        Freq = float(base.filter(WordType=self).count())/float(base.filter(~Q(Category__CategoryType='Other'),~Q(Category__CategoryType='Pause'),~Q(Category__CategoryType='Disfluency')).count())
        Freq = math.log((Freq * 1000000)+1,10)
        if subset=='all':
            self.Frequency = Freq
            self.save()
        return Freq

    def getNDs(self,subset='all',speaker=None,dialog=None):
        if subset == 'all' and self.ND is not None and self.FWND is not None:
            return self.ND,self.FWND
        any_segment = '[A-Za-z]{1,2}'
        phones = map(str,self.UR.all())
        patterns = []
        for i in range(len(phones)):
            patt = phones[:i] #Substitutions
            patt.append(any_segment)
            patt.extend(phones[i+1:])
            patterns.append('^'+' '.join(patt) +'$')
            patt = phones[:i] #Deletions
            patt.extend(phones[i+1:])
            patterns.append('^'+' '.join(patt) +'$')
            patt = phones[:i] #Insertions
            patt.append(any_segment)
            patt.extend(phones[i:])
            patterns.append('^'+' '.join(patt) +'$')
        neighs = WordType.objects.filter(Label__regex="^[^{<]").extra(
                    where = [UR_LOOKUP],
                    params = ['|'.join(patterns)])
        freqs = [ x.getFreq(subset=subset,speaker=speaker,dialog=dialog) for x in neighs]
        nd = sum([1 for x in freqs if x > 0])
        fwnd = sum(freqs)
        if subset == 'all':
            self.ND,self.FWND = nd,fwnd
            self.save()
        return nd,fwnd

    def getND(self,subset='all',speaker=None,dialog=None):
        if subset == 'all' and self.ND is not None:
            return self.ND
        nd,fwnd = self.getNDs(subset=subset,speaker=speaker,dialog=dialog)
        return nd

    def getFWND(self,subset='all',speaker=None,dialog=None):
        if subset == 'all' and self.FWND is not None:
            return self.FWND
        nd,fwnd = self.getNDs(subset=subset,speaker=speaker,dialog=dialog)
        return fwnd

    def getPhonoProb(self,subset='all',speaker=None,dialog=None):
        if subset == 'all' and self.SPhonoProb is not None and self.BiPhonoProb is not None:
            return self.SPhonoProb,self.BiPhonoProb
        base = WordType.objects.filter(Label__regex="^[^{<]")
        if subset == 'gender' and speaker is not None:
            base = base.filter(wordtoken__Dialog__Speaker__Gender = speaker.Gender)
        elif subset == 'age' and speaker is not None:
            base = base.filter(wordtoken__Dialog__Speaker__Age = speaker.Age)
        elif subset == 'speaker' and speaker is not None:
            base = base.filter(wordtoken__Dialog__Speaker = speaker)
        elif subset == 'dialog' and dialog is not None:
            base = base.filter(wordtoken__Dialog = dialog)
        base = base.annotate(num = Count('wordtoken'))
        any_segment = '[A-Za-z]{1,2}'
        patterns = []
        SPprob = 0.0
        BPprob = 0.0
        phones = map(str,self.UR.all())
        allwords = float(base.aggregate(totcount=Sum('num'))['totcount'])
        for i in range(len(phones)):
            patt = [any_segment] * i
            patt.append(phones[i])
            pattern = '^'+' '.join(patt) +'.*$'
            totPattern = '^'+' '.join([any_segment] * (i+1)) +'.*$'
            count = base.extra(
                    where = [UR_LOOKUP],
                    params = [pattern])
            totCount = base.extra(
                    where = [UR_LOOKUP],
                    params = [totPattern])
            countFreqs = [math.log(((float(x.num)/allwords) * 1000000)+1,10)
                                for x in count]
            totFreqs = [math.log(((float(x.num)/allwords) * 1000000)+1,10)
                                for x in totCount]
            SPprob += float(sum(countFreqs)) / float(sum(totFreqs))
            if i != len(phones)-1:
                patt = [any_segment] * i
                patt.extend([phones[i],phones[i+1]])
                pattern = '^'+' '.join(patt) +'.*$'
                totPattern = '^'+' '.join([any_segment] * (i+2)) +'.*$'
                count = base.extra(
                    where = [UR_LOOKUP],
                    params = [pattern])
                totCount = base.extra(
                    where = [UR_LOOKUP],
                    params = [totPattern])
                countFreqs = [math.log(((float(x.num)/allwords) * 1000000)+1,10)
                                for x in count]
                totFreqs = [math.log(((float(x.num)/allwords) * 1000000)+1,10)
                                for x in totCount]
                BPprob += float(sum(countFreqs)) / float(sum(totFreqs))
        SPprob = SPprob / float(len(phones))
        BPprob = BPprob / float(len(phones)-1)
        if subset == 'all':
            self.SPhonoProb,self.BiPhonoProb = SPprob,BPprob
            self.save()
        return SPprob,BPprob


class WordToken(caching.base.CachingMixin,models.Model):
    SR = models.ManyToManyField(SegmentType,through=SegmentToken)
    Begin = models.FloatField()
    End = models.FloatField()
    WordType = models.ForeignKey(WordType)
    Category = models.ForeignKey(Category)
    Dialog = models.ForeignKey(Dialog)
    DialogPart = models.CharField(max_length=1)
    StrVowelF1 = models.FloatField(blank=True,null=True)
    StrVowelF2 = models.FloatField(blank=True,null=True)
    PrevSemPred = models.FloatField(blank=True,null=True)
    FollSemPred = models.FloatField(blank=True,null=True)
    NumFormants = models.DecimalField('Number of formants',max_digits=4,decimal_places=1,blank=True,null=True)
    Ceiling = models.IntegerField(blank=True,null=True)
    Output = PickledObjectField(null=True)

    objects = caching.base.CachingManager()

    def __unicode__(self):
        return u'%s' % unicode(self.WordType)

    def setSpecVariables(self,ceiling,numformants):
        self.Ceiling = ceiling
        self.NumFormants = numformants
        self.save()

    def getNFormants(self):
        if self.NumFormants is not None:
            return self.NumFormants
        return self.Dialog.Speaker.NumFormants

    def getCeiling(self):
        if self.Ceiling is not None:
            return self.Ceiling
        return self.Dialog.Speaker.Ceiling

    def getStrF1(self):
        if self.StrVowelF1 is None:
            self.setStrFormants()
        return self.StrVowelF1

    def getStrF2(self):
        if self.StrVowelF2 is None:
            self.setStrFormants()
        return self.StrVowelF2

    def getPrevSemPred(self,style='A',window='A'):
        if style == 'A' and window == 'A':
            if self.PrevSemPred is not None:
                return self.PrevSemPred
        if window != 'A':
            prev_context = self.getPreviousContext(window = int(window))
        else:
            prev_context = self.getPreviousContext()
        #catted = categorize_words([str(x)
        #                        for x in prev_context
        #                            if str(x) != str(self)]
        #                        + [str(self)])

        #cat_word = catted.pop(-1)
        #tagged_context = ['#'.join([x,'1']) for x in
        #                    catted
        #                    if x[-2] == '#' and x[-1] in ['n','v','a','r']]
        prev_context = filter(lambda x: x.getCelexCat() in ['N','V','A','ADV'],prev_context)
        tagged_context = map(lambda x: '#'.join([str(x),
                                                x.getCelexCat().lower().replace('adv','r'),
                                                '1']),prev_context)
        cat_word = '#'.join([str(self),self.getCelexCat(),'1'])
        if cat_word.endswith('na#1'):
            cat = self.Category.Label
            if 'N' in cat:
                cat = 'n'
            elif 'JJ' in cat:
                cat = 'a'
            elif 'VB' in cat:
                cat = 'v'
            elif 'RB' in cat:
                cat = 'r'
            else:
                cat = 'NA'
            cat_word  = '#'.join([cat_word.split("#")[0],cat,'1'])
        sp = getSemanticRelatedness(cat_word,tagged_context,style=style)
        if style == 'A' and window == 'A':
            self.PrevSemPred = sp
            self.save()
            return self.PrevSemPred
        return sp

    def getFollSemPred(self,style='A',window='A'):
        if style == 'A' and window == 'A':
            if self.FollSemPred is not None:
                return self.FollSemPred
        if window != 'A':
            foll_context = self.getFollowingContext(window = int(window))
        else:
            foll_context = self.getFollowingContext()
        #catted = categorize_words([str(x)
        #                        for x in foll_context
        #                            if str(x) != str(self)]
        #                        + [str(self)])

        #cat_word = catted.pop(-1)
        #tagged_context = ['#'.join([x,'1']) for x in
        #                    catted
        #                    if x[-2] == '#' and x[-1] in ['n','v','a','r']]
        foll_context = filter(lambda x: x.getCelexCat() in ['N','V','A','ADV'],foll_context)
        tagged_context = map(lambda x: '#'.join([str(x),
                                                x.getCelexCat().lower().replace('adv','r'),
                                                '1']),foll_context)
        cat_word = '#'.join([str(self),self.getCelexCat(),'1'])
        if cat_word.endswith('na#1'):
            cat = self.Category.Label
            if 'N' in cat:
                cat = 'n'
            elif 'JJ' in cat:
                cat = 'a'
            elif 'VB' in cat:
                cat = 'v'
            elif 'RB' in cat:
                cat = 'r'
            else:
                cat = 'NA'
            cat_word  = '#'.join([cat_word.split("#")[0],cat,'1'])
        sp = getSemanticRelatedness(cat_word,tagged_context,style=style)
        if style == 'A' and window == 'A':
            self.FollSemPred = sp
            self.save()
            return self.FollSemPred
        return sp

    def setStrFormants(self,formants=None):
        if formants is not None:
            self.StrVowelF1 = formants[0]
            self.StrVowelF2 = formants[1]
            self.save()
        else:
            p = PraatLoader(settings.PRAAT_PATH,debug=settings.DEBUG)
            path = str(self.Dialog.Speaker) + "/" + str(self.Dialog)+self.DialogPart
            begin,end = self.getStressedVowelInfo()
            ceiling = self.getCeiling()
            nformants = self.getNFormants()
            out = p.get_formants(fetch_buckeye_resource("Speakers/"+path+'.wav'),begin,end,nformants,ceiling)
            dur = float(end)-float(begin)
            if dur > 0.0 and len(out) > 0:
                fones = [x['F1(Hz)'] for x in out if x['F1(Hz)'] != '--undefined--' and float(x['time(s)'])/dur> 0.25 and float(x['time(s)'])/dur < 0.75]
                ftwos = [x['F2(Hz)'] for x in out if x['F2(Hz)'] != '--undefined--' and float(x['time(s)'])/dur> 0.25 and float(x['time(s)'])/dur < 0.75]
                if len(fones) > 0 and len(ftwos) > 0:
                    self.StrVowelF1 = sum(map(float,fones))/float(len(fones))
                    self.StrVowelF2 = sum(map(float,ftwos))/float(len(ftwos))
                    self.save()

    def hasStress(self):
        for s in self.segmenttoken_set.all():
            if s.Stressed:
                return True
        return False

    def getStrVowel(self):
        pass

    def getSR(self):
        return ".".join([unicode(s) for s in self.SR.all()])

    def getStressedVowelInfo(self,cvc=True):
        if cvc:
            qs = self.segmenttoken_set.filter(SegmentType__Vowel=True)
            if len(qs) > 0:
                return qs[0].Begin,qs[0].End
            else:
                return 0.0,0.0
        if self.hasStress():
            qs = self.segmenttoken_set.get(Stressed=True)
            print qs
            return qs.Begin,qs.End
        ur = self.WordType.underlying_set.all()
        sr = self.segmenttoken_set.all()
        score,mapping = DTW(map(str,[x.SegmentType for x in ur]),map(str,[x.SegmentType for x in sr]),distOnly=False)
        ui = 0
        sj = 0
        for m in mapping:
            if m[0] == str(ur[ui]):
                if m[1] != '.' and ur[ui].Stressed == 1:

                    sr[sj].Stressed = True
                    sr[sj].save()
                ui += 1
            if m[1] == str(sr[sj]):
                sj += 1

        return self.getStressedVowelInfo()

    def getDialogPath(self):
        path = fetch_buckeye_resource("Speakers/"+str(self.Dialog.Speaker) + "/" + str(self.Dialog)+self.DialogPart + ".wav")
        return path

    def getAcousticInfo(self):
        sr = self.segmenttoken_set.all()
        begin = None
        for s in xrange(len(sr)):
            if sr[s].SegmentType.isVowel():
                prevSound = sr[s-1].SegmentType.Label
                vow = sr[s].SegmentType.Label
                follSound = sr[s+1].SegmentType.Label
                begin = sr[s].Begin
                end = sr[s].End
        return begin,end,vow,prevSound,follSound

    def getPreviousWord(self):
        if self.DialogPart == 'b' and self.Begin == 0.0:
            prev = WordToken.objects.select_related('Category','WordType').filter(Dialog=self.Dialog).filter(DialogPart='a').order_by('-Begin')
        else:
            prev = WordToken.objects.select_related('Category','WordType').filter(Dialog=self.Dialog).filter(pk=self.pk-1)
        if len(prev) > 0:
            return prev[0]
        return None

    def getFollowingWord(self):
        foll = WordToken.objects.select_related('Category','WordType').filter(Dialog=self.Dialog).filter(pk=self.pk+1)
        if self.DialogPart == 'a' and len(foll) == 0:
            foll = WordToken.objects.select_related('Category','WordType').filter(Dialog=self.Dialog).filter(DialogPart='b').filter(Begin__exact=0.0)
        if len(foll) > 0:
            return foll[0]
        return None

    def getPreviousContext(self,window='auto'):
        if window == 'auto':
            window_max = 10
        else:
            window_max = window
        context = []
        prev = self.getPreviousWord()
        durSum = prev.getDuration()
        while durSum <= window_max:
            if prev is None:
                break
            if prev.WordType.isWord():
                context.append(prev)
            durSum += prev.getDuration()
            if window == 'auto' and prev.afterPause():
                break
            prev = prev.getPreviousWord()
        return reversed(context)

    def getFollowingContext(self,window='auto'):
        if window == 'auto':
            window_max = 10
        else:
            window_max = window
        context = []
        foll = self.getFollowingWord()
        durSum = foll.getDuration()
        while durSum <= window_max:
            if foll is None:
                break
            if foll.WordType.isWord():
                context.append(foll)
            durSum += foll.getDuration()
            if window == 'auto' and foll.beforePause():
                break
            foll = foll.getFollowingWord()
        return context

    def getRecentRepetition(self):
        cont = set(map(str,self.getPreviousContext()))
        if str(self) in cont:
            return True
        return False

    def getRepetitions(self):
        reps = WordToken.objects.filter(Dialog=self.Dialog).filter(DialogPart=self.DialogPart).filter(End__lte=self.Begin).filter(WordType=self.WordType).count()
        if self.DialogPart == 'b':
            reps = reps + WordToken.objects.filter(Dialog=self.Dialog).filter(DialogPart='a').filter(WordType=self.WordType).count()
        return reps

    def getDialogPlace(self):
        diagPlace = self.Begin
        if self.DialogPart == 'b':
            aDiag = WordToken.objects.filter(Dialog=self.Dialog).filter(DialogPart='a').order_by('-Begin')
            if len(aDiag) > 0:
                lengthOfA = aDiag[0].End
                diagPlace += lengthOfA
        return diagPlace

    def getNumSylls(self):
        numSylls = 0
        for seg in self.SR.all():
            if seg.isSyllabic():
                numSylls += 1
        return numSylls

    def getDuration(self):
        return self.End - self.Begin

    def afterPause(self):
        if self.getPreviousWord() is None:
            return True
        if self.getPreviousWord().Category.CategoryType == "Disfluency":
            return True
        if self.getPreviousWord().Category.CategoryType == "Other":
            return True
        if self.getPreviousWord().Category.CategoryType == "Pause":
            if self.getPreviousWord().getDuration() >= 0.5:
                return True
        return False

    def beforePause(self):
        if self.getFollowingWord() is None:
            return True
        if self.getFollowingWord().Category.CategoryType == "Disfluency":
            return True
        if self.getFollowingWord().Category.CategoryType == "Other":
            return True
        if self.getFollowingWord().Category.CategoryType == "Pause":
            if self.getFollowingWord().getDuration() >= 0.5:
                return True
        return False

    def nextToPause(self):
        if self.afterPause():
            return True
        if self.beforePause():
            return True
        return False

    def getPreviousSpeakingRate(self):
        prev_context = self.getPreviousContext()
        total_syllables = float(sum([x.getNumSylls() for x in prev_context]))
        total_seconds = self.getPrevDistToPause()
        if total_seconds != 0.0:
            rate = total_syllables / total_seconds
        else:
            rate = 0.0
        return rate

    def getFollowingSpeakingRate(self):
        foll_context = self.getFollowingContext()
        total_syllables = float(sum([x.getNumSylls() for x in foll_context]))
        total_seconds = self.getFollDistToPause()
        if total_seconds != 0.0:
            rate = total_syllables / total_seconds
        else:
            rate = 0.0
        return rate

    def getPrevDistToPause(self):
        if self.afterPause():
            return 0.0
        return sum([x.getDuration() for x in self.getPreviousContext()])

    def getFollDistToPause(self):
        if self.beforePause():
            return 0.0
        return sum([x.getDuration() for x in self.getFollowingContext()])

    def getPreviousCondProb(self):
        if self.afterPause():
            return 0.0
        if not self.getPreviousWord().WordType.isWord():
            return 0.0
        prev = self.getPreviousWord()
        pc = PrevCondProbs.objects.get_or_create(ActWord=self.WordType,PreviousWord=prev.WordType)[0]
        return pc.getProb()

    def getFollowingCondProb(self):
        if self.beforePause():
            return 0.0
        foll = self.getFollowingWord()
        fc = FollCondProbs.objects.get_or_create(ActWord=self.WordType,FollowingWord=foll.WordType)[0]
        return fc.getProb()

    def createPictures(self):
        p = PraatLoader(settings.PRAAT_PATH,debug=settings.DEBUG)
        wavpath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+".wav")
        outpath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+".mp3")
        specepspath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+"-spectro.eps")
        specpath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+"-spectro.png")
        wfepspath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+"-waveform.eps")
        waveformpath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+"-waveform.png")
        filename = self.getDialogPath()
        beg = self.Begin
        end = self.End
        ceiling = self.getCeiling()
        nformants = self.getNFormants()
        if not os.path.isfile(wavpath):
            p.extract_token(filename, beg, end, wavpath)
        if not os.path.isfile(waveformpath):
            p.waveform_pic(wavpath,','.join([str(x.End-self.Begin) for x in self.segmenttoken_set.all()]))
            im = Image.open(wfepspath)
            im.save(waveformpath)
            os.remove(wfepspath)
        p.spectro_pic(wavpath,1,nformants,ceiling,','.join([str(x.End-self.Begin) for x in self.segmenttoken_set.all()]))
        im = Image.open(specepspath)
        im.save(specpath)
        os.remove(specepspath)
        if not os.path.isfile(outpath):
            p.convert_MP3(wavpath)
        #decoder  =  timeside.decoder.FileDecoder(wavpath)
        #grapher  =  timeside.grapher.Waveform()
        #spectrogram = timeside.grapher.Spectrogram(width=400,height=100)
        #encoder  =  timeside.encoder.Mp3Encoder(outpath)
        #(decoder | grapher).run()
        #print ton
        #grapher.render(output=waveformpath)
        #spectrogram.render().save(specpath)

    def isAcceptable(self):
        if self.nextToPause():
            return False
        if len(self.WordType.getCVSkel()) < 3:
            return False
        return True

    def getCelexCat(self):
        if self.Output is None:
            self.Output = {}
        if 'CelexCategory' not in self.Output:
            cat = lookupCat(self.WordType.Label)
            self.Output['CelexCategory'] = cat
            self.save()
        return self.Output['CelexCategory']

    def getAnalysisLines(self,output_form):
        form = output_form.cleaned_data
        wanted_fields = output_form.get_wanted_fields()
        if self.Output is not None:
            outline = copy.copy(self.Output)
        else:
            outline = {}

        if outline == {}:
            outline['Word'] = self.WordType.Label
            outline['Token'] = self.pk
            outline['Speaker'] = str(self.Dialog.Speaker)
            if form['measure'] != 'N':
                beg,end,vow,prevSound,follSound = self.getAcousticInfo()
                outline['Vowel'] = self.WordType.getStressVowel()
                outline['PrevCons'] = prevSound
                outline['FollCons'] = follSound
        if form['segmentalDurations']:
            if 'VowDur' not in outline:
                outline['VowDur'] = end-beg
                outline['OtherDur'] = self.getDuration()- outline['VowDur']
        if form['speakingRates']:
            if 'PrevSpeakRate' not in outline:
                outline['PrevSpeakRate'] = self.getPreviousSpeakingRate()
                outline['FollSpeakRate'] = self.getFollowingSpeakingRate()
                outline['AvgSpeakRate'] = self.Dialog.Speaker.getAvgSpeakingRate()
        if form['contextProbs']:
            if 'PrevCondProb' not in outline:
                outline['PrevCondProb'] = self.getPreviousCondProb()
                outline['FollCondProb'] = self.getFollowingCondProb()
        if form['repetitions']:
            if 'Repetitions' not in outline:
                outline['Repetitions'] = self.getRepetitions()
                outline['wasRepeatedRecently'] = self.getRecentRepetition()
        if form['wasRepeated']:
            if 'Repetitions' not in outline:
                outline['Repetitions'] = self.getRepetitions()
            if 'wasRepeated' not in outline:
                if outline['Repetitions'] != 0:
                    outline['wasRepeated'] = 'True'
                else:
                    outline['wasRepeated'] = 'False'
        if 'CelexCategory' not in outline:
            cat = lookupCat(self.WordType.Label)
            outline['CelexCategory'] = cat
        if outline['CelexCategory'] not in ['N','ADV','A','V']:
            return None

        if 'C' in form['lexical_scale']:
            celex_info = get_lexical_info(self.WordType.Label)

        if 'B' in form['category']:
            if 'BuckeyeCategory' not in outline:
                outline['BuckeyeCategory'] = self.Category.Label

        if form['wordDuration']:
            if 'WordDuration' not in outline:
                outline['WordDuration'] = self.getDuration()
                outline['BaselineDur'] = self.WordType.getBaseDuration()

        if form['frequency']:
            if 'C' in form['lexical_scale'] and 'CelexFrequency' not in outline:
                try:
                    outline['CelexFrequency'] = celex_info['Freq']
                except KeyError:
                    outline['CelexFrequency'] = 'NA'
            if 'W' in form['lexical_scale'] and 'BuckeyeFrequency' not in outline:
                outline['BuckeyeFrequency'] = self.WordType.getFreq()
            if 'S' in form['lexical_scale'] and 'SpeakerFrequency' not in outline:
                outline['SpeakerFrequency'] = self.WordType.getFreq(subset='speaker',speaker=self.Dialog.Speaker)
            if 'A' in form['lexical_scale'] and 'AgeFrequency' not in outline:
                outline['AgeFrequency'] = self.WordType.getFreq(subset='age',speaker=self.Dialog.Speaker)
            if 'G' in form['lexical_scale'] and 'GenderFrequency' not in outline:
                outline['GenderFrequency'] = self.WordType.getFreq(subset='gender',speaker=self.Dialog.Speaker)
            if 'D' in form['lexical_scale'] and 'DialogFrequency' not in outline:
                outline['DialogFrequency'] = self.WordType.getFreq(subset='dialog',speaker=self.Dialog.Speaker,dialog=self.Dialog)

        if form['gender']:
            if 'SpeakerGender' not in outline:
                outline['SpeakerGender'] = self.Dialog.Speaker.Gender
        if form['age']:
            if 'SpeakerAge' not in outline:
                outline['SpeakerAge'] = self.Dialog.Speaker.Age

        if form['orthoLength']:
            if 'OrthoLength' not in outline:
                outline['OrthoLength'] = len(self.WordType.Label)
        if form['phonoLength']:
            if 'PhonoLength' not in outline:
                outline['PhonoLength'] = self.WordType.UR.count()
        if form['nd']:
            if 'C' in form['lexical_scale'] and 'CelexNeighDen' not in outline:
                try:
                    outline['CelexNeighDen'],outline['CelexFWND'] = celex_info['ND'],celex_info['FWND']
                except KeyError:
                    outline['CelexNeighDen'],outline['CelexFWND'] = 'NA','NA'
            if 'W' in form['lexical_scale'] and 'BuckeyeNeighDen' not in outline:
                outline['BuckeyeNeighDen'],outline['BuckeyeFWND'] = self.WordType.getNDs()
            if 'S' in form['lexical_scale'] and 'SpeakerNeighDen' not in outline:
                outline['SpeakerNeighDen'],outline['SpeakerFWND'] = self.WordType.getNDs(subset='speaker',speaker=self.Dialog.Speaker)
            if 'A' in form['lexical_scale'] and 'AgeNeighDen' not in outline:
                outline['AgeNeighDen'],outline['AgeFWND'] = self.WordType.getNDs(subset='age',speaker=self.Dialog.Speaker)
            if 'G' in form['lexical_scale'] and 'GenderNeighDen' not in outline:
                outline['GenderNeighDen'],outline['GenderFWND'] = self.WordType.getNDs(subset='gender',speaker=self.Dialog.Speaker)
            if 'D' in form['lexical_scale'] and 'DialogNeighDen' not in outline:
                outline['DialogNeighDen'],outline['DialogFWND'] = self.WordType.getNDs(subset='dialog',speaker=self.Dialog.Speaker,dialog=self.Dialog)

        if form['phonotactic']:
            if 'C' in form['lexical_scale'] and 'CelexSPhoneProb' not in outline:
                try:
                    outline['CelexSPhoneProb'],outline['CelexBiPhoneProb'] = celex_info['SP'],celex_info['BP']
                except KeyError:
                    outline['CelexSPhoneProb'],outline['CelexBiPhoneProb'] = 'NA','NA'
            if 'W' in form['lexical_scale'] and 'BuckeyeSPhoneProb' not in outline:
                outline['BuckeyeSPhoneProb'],outline['BuckeyeBiPhoneProb'] = self.WordType.getPhonoProb()
            if 'S' in form['lexical_scale'] and 'SpeakerSPhoneProb' not in outline:
                qs = WordToken.objects.filter(Dialog__Speaker= self.Dialog.Speaker).filter(WordType=self.WordType).order_by('Dialog')
                for q in qs:
                    if q.Output is not None and 'SpeakerSPhoneProb' in q.Output:
                        outline['SpeakerSPhoneProb'],outline['SpeakerBiPhoneProb'] = q.Output['SpeakerSPhoneProb'],q.Output['SpeakerBiPhoneProb']
                        break
                else:
                    outline['SpeakerSPhoneProb'],outline['SpeakerBiPhoneProb'] = self.WordType.getPhonoProb(subset='speaker',speaker=self.Dialog.Speaker)
            if 'A' in form['lexical_scale'] and 'AgeSPhoneProb' not in outline:
                qs = WordToken.objects.filter(Dialog__Speaker__Age= self.Dialog.Speaker.Age).filter(WordType=self.WordType).order_by('Dialog')
                for q in qs:
                    if q.Output is not None and 'AgeSPhoneProb' in q.Output:
                        outline['AgeSPhoneProb'],outline['AgeBiPhoneProb'] = q.Output['AgeSPhoneProb'],q.Output['AgeBiPhoneProb']
                        break
                else:
                    outline['AgeSPhoneProb'],outline['AgeBiPhoneProb'] = self.WordType.getPhonoProb(subset='age',speaker=self.Dialog.Speaker)
            if 'G' in form['lexical_scale'] and 'GenderSPhoneProb' not in outline:
                qs = WordToken.objects.filter(Dialog__Speaker__Gender= self.Dialog.Speaker.Gender).filter(WordType=self.WordType).order_by('Dialog')
                for q in qs:
                    if q.Output is not None and 'GenderSPhoneProb' in q.Output:
                        outline['GenderSPhoneProb'],outline['GenderBiPhoneProb'] = q.Output['GenderSPhoneProb'],q.Output['GenderBiPhoneProb']
                        break
                else:
                    outline['GenderSPhoneProb'],outline['GenderBiPhoneProb'] = self.WordType.getPhonoProb(subset='gender',speaker=self.Dialog.Speaker)
            if 'D' in form['lexical_scale'] and 'DialogSPhoneProb' not in outline:
                outline['DialogSPhoneProb'],outline['DialogBiPhoneProb'] = self.WordType.getPhonoProb(subset='dialog',speaker=self.Dialog.Speaker,dialog=self.Dialog)

        if form['additional_phono_stats']:
            if 'PhonoStatsNeighDen' not in outline:
                outline['PhonoStatsNeighDen'] = getNeighCount(self.WordType.getUR(
                                                        stressed=True,blick_style=True),no_stress=True)
            if 'PhonoStatsBlickPhono' not in outline:
                outline['PhonoStatsBlickPhono'] = getPhonotacticProb(self.WordType.getUR(
                                                        stressed=True,blick_style=True),
                                                        use_blick=True,no_stress=True)
            if 'PhonoStatsSPhoneProb' not in outline:
                outline['PhonoStatsSPhoneProb'],outline['PhonoStatsBiPhoneProb'] = getPhonotacticProb(self.WordType.getUR(
                                                        stressed=True,blick_style=True),use_blick=False,no_stress=True)

        for w in eval(form['sem_pred_window']):
            for s in eval(form['sem_pred_style']):
                if form['prev_sem_pred']:
                    label = '%sWindowPrev%sSemPred' %(w,s)
                    if label not in outline:
                        outline[label] = self.getPrevSemPred(window = w,style=s)
                if form['foll_sem_pred']:
                    label = '%sWindowFoll%sSemPred' %(w,s)
                    if label not in outline:
                        outline[label] = self.getFollSemPred(window = w,style=s)
        if form['pause_dist']:
            if 'DistFollPause' not in outline:
                outline['DistFollPause'] = self.getFollDistToPause()
            if 'DistPrevPause' not in outline:
                outline['DistPrevPause'] = self.getPrevDistToPause()
        if form['placeInDialog']:
            if 'placeInDialog' not in outline:
                outline['placeInDialog'] = self.getDialogPlace()
        if form['measure'] == 'S':
            if 'formants' not in outline:
                ceiling = self.getCeiling()
                nformants = self.getNFormants()
                outline['formants'] = [ {'time(s)':x['time(s)'],
                            'F1(Hz)':x['F1(Hz)'],
                            'F2(Hz)':x['F2(Hz)']}
                            for x in p.get_formants(self.getDialogPath(),beg,end,nformants,ceiling)
                                if x['F1(Hz)'] != '--undefined--' and x['F2(Hz)'] != '--undefined--']
            to_out = [ {'time':x['time(s)'],
                            'F1':x['F1(Hz)'],
                            'F2':x['F2(Hz)']}.update({k:outline[k] for k in outline
                                                            if k != 'formants' and k in wanted_fields})
                            for x in outline['formants']]
        elif form['measure'] != 'N':
            if 'F1' not in outline:
                F1 = self.getStrF1()
                F2 = self.getStrF2()
                if F1 is None:
                    outline['F1'] = 'NA'
                else:
                    outline['F1'] = F1
                if F2 is None:
                    outline['F2'] = 'NA'
                else:
                    outline['F2'] = F2
            if form['measure'] == 'D' and 'NA' not in [outline['F1'],outline['F2']]:
                if form['DispersionFromAH']:
                    if 'AHDispersion' not in outline:
                        center = self.Dialog.Speaker.getAHCenter()
                        outline['AHDispersion'] = math.sqrt(math.pow(outline['F1']-center[0],2)+math.pow(outline['F2']-center[1],2))

                else:
                    if 'Dispersion' not in outline:
                        center = self.Dialog.Speaker.getCenter()
                        outline['Dispersion'] = math.sqrt(math.pow(outline['F1']-center[0],2)+math.pow(outline['F2']-center[1],2))

            elif form['measure'] == 'D':
                outline['Dispersion'] = 'NA'
        to_out = [{k:outline[k] for k in outline if k in wanted_fields}]
        if self.Output is None or outline.keys() != self.Output.keys():
            self.Output = outline
            self.save()
        return to_out

    def remove_field_from_output(self,f):
        if f in self.Output:
            self.Output = {x: self.Output[x] for x in self.Output if x != f}
            self.save()

    def get_details(self):
        if self.WordType.isWord():
            sp,bp = self.WordType.getPhonoProb()
            cont = OrderedDict([('Previous conditional probability', self.getPreviousCondProb()),
                        ('Following conditional probability', self.getFollowingCondProb()),
                        ('Previous speaking rate', self.getPreviousSpeakingRate()),
                        ('Following speaking rate', self.getFollowingSpeakingRate()),
                        ('Previous distance to pause', self.getPrevDistToPause()),
                        ('Following distance to pause', self.getFollDistToPause()),
                        ('Previous semantic predictability', self.getPrevSemPred()),
                        ('Following semantic predictability',self.getFollSemPred())])
            lex = OrderedDict([('Word', str(self.WordType)),
                            ('Underlying representation', self.WordType.getUR()),
                            ('Buckeye frequency', self.WordType.getFreq()),
                            ('Buckeye single-phone probability', sp),
                            ('Buckeye bi-phone probability', bp),
                            ('Buckeye neighbourhood density', self.WordType.getND()),
                            ('Buckeye frequency-weighted neighbourhood density', self.WordType.getFWND()),
                            ('Stress vowel', self.WordType.getStressVowel())])
            tok = OrderedDict([('Dialog', str(self.Dialog)),
                            ('Surface representation', self.getSR()),
                            ('Buckeye category', str(self.Category)),
                            ('Stress vowel F1', self.getStrF1()),
                            ('Stress vowel F2', self.getStrF2()),
                            ('Repetitions', self.getRepetitions()),
                            ('Given', self.getRecentRepetition())])
            speak = OrderedDict([('Speaker', str(self.Dialog.Speaker)),
                            ('Gender', self.Dialog.Speaker.Gender),
                            ('Age', self.Dialog.Speaker.Age),
                            ('Number of formants', self.Dialog.Speaker.NumFormants),
                            ('Formant ceiling', self.Dialog.Speaker.Ceiling),
                            ('Vowel center', self.Dialog.Speaker.getCenter()),
                            ('Average speaking rate', self.Dialog.Speaker.getAvgSpeakingRate())])
            out = {'Preceding': self.getPreviousContext(),
                    'Following': self.getFollowingContext(),
                    'Word': str(self.WordType),
                    'NFormants': self.getNFormants(),
                    'Ceiling': self.getCeiling(),
                    'TokenID': self.pk,
                    'Contextual': cont,
                    'Lexical':lex,
                    'Token':tok,
                    'Speaker':speak}
        else:
            cont = OrderedDict([('Previous speaking rate', self.getPreviousSpeakingRate()),
                        ('Following speaking rate', self.getFollowingSpeakingRate()),
                        ('Previous distance to pause', self.getPrevDistToPause()),
                        ('Following distance to pause', self.getFollDistToPause())])
            tok = OrderedDict([('Dialog', str(self.Dialog)),
                            ('Buckeye category', str(self.Category))])
            speak = OrderedDict([('Speaker', str(self.Dialog.Speaker)),
                            ('Gender', self.Dialog.Speaker.Gender),
                            ('Age', self.Dialog.Speaker.Age),
                            ('Number of formants', self.Dialog.Speaker.NumFormants),
                            ('Formant ceiling', self.Dialog.Speaker.Ceiling),
                            ('Vowel center', self.Dialog.Speaker.getCenter()),
                            ('Average speaking rate', self.Dialog.Speaker.getAvgSpeakingRate())])
            out = {'Preceding': self.getPreviousContext(),
                    'Following': self.getFollowingContext(),
                    'Word': str(self.WordType),
                    'NFormants': self.Dialog.Speaker.NumFormants,
                    'Ceiling': self.Dialog.Speaker.Ceiling,
                    'TokenID': self.pk,
                    'Contextual':cont,
                'Token':tok,
                'Speaker':speak}

        return out
