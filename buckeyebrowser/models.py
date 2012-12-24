from django.db import models

# Create your models here.

from LingToolsWebsite.managers import BulkManager

from django.conf import settings
import os,Image#,re,csv,timeside

import math
from django.db.models import Count,Sum,Q
from StimuliPicker.stimuli.functions import lookupStress,lookupCat
from LingToolsWebsite.functions import DTW,getSemanticRelatedness,fetch_media_resource
from funcs import costs
from PraatInterface.Praat import PraatLoader
from blick import BlickLoader

p = PraatLoader(fetch_media_resource('PraatScripts/'),fetch_media_resource("Tools/praat"))
b = BlickLoader()

class WTManager(BulkManager):
    tbl_name = "buckeye_wordtoken"
    cols = ['id','Begin','End','WordType_id','Category_id','Dialog_id','DialogPart']

class STManager(BulkManager):
    tbl_name = "buckeye_segmenttoken"
    cols = ['id','WordToken_id','SegmentType_id','Begin','End']

class PCManager(BulkManager):
    tbl_name = 'buckeye_prevcondprobs'
    cols = ['id','ActWord_id','PreviousWord_id','Count','Prob']
    
class FCManager(BulkManager):
    tbl_name = 'buckeye_follcondprobs'
    cols = ['id','ActWord_id','FollowingWord_id','Count','Prob']

class Speaker(models.Model):
    Number = models.CharField(max_length=3)
    Gender = models.CharField(max_length=10)
    Age = models.CharField(max_length=10)
    NumFormants = models.DecimalField('Number of formants',max_digits=4,decimal_places=1)
    Ceiling = models.IntegerField()
    F1center = models.FloatField(blank=True,null=True)
    F2center = models.FloatField(blank=True,null=True)
    AvgSpeakingRate = models.FloatField(blank=True,null=True)
    
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
        cursor.execute("""Select avg(AvgF1), avg(AvgF2) FROM (SELECT StressVowel as Vowel,
avg(StrVowelF1) as AvgF1,
avg(StrVowelF2) as AvgF2
 FROM LingToolsWebsite.buckeye_wordtoken
Inner join buckeye_wordtype
ON buckeye_wordtype.id =buckeye_wordtoken.WordType_id
Inner join buckeye_dialog
ON buckeye_dialog.id = buckeye_wordtoken.Dialog_id
Inner join buckeye_speaker
ON buckeye_speaker.id = buckeye_dialog.Speaker_id
WHERE CVSkel = 'CVC'
AND buckeye_dialog.Speaker_id = %s
Group by StressVowel) AS averages""",[self.pk])
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
        
        
        
    
class Dialog(models.Model):
    Speaker = models.ForeignKey(Speaker)
    Number = models.CharField(max_length=10)
    
    def __unicode__(self):
        return u'%s%s' % (self.Speaker,self.Number)

class SegmentType(models.Model):
    Label = models.CharField(max_length=10)
    Syllabic = models.BooleanField()
    Obstruent = models.BooleanField()
    Nasal = models.BooleanField()
    Vowel = models.BooleanField()
    
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

class Underlying(models.Model):
    WordType = models.ForeignKey('WordType')
    SegmentType = models.ForeignKey(SegmentType)
    Ordering = models.IntegerField()
    Stressed = models.IntegerField(blank=True,null=True)
    
    def getStrTrans(self):
        if self.Stressed is None:
            return str(self.SegmentType).upper()
        return str(self.SegmentType).upper()+str(self.Stressed)
    
    class Meta:
        ordering = ['Ordering']

class SegmentToken(models.Model):
    WordToken = models.ForeignKey('WordToken')
    SegmentType = models.ForeignKey(SegmentType)
    Begin = models.FloatField()
    End = models.FloatField()
    Stressed = models.NullBooleanField()
    
    objects = STManager()
    
    def __unicode__(self):
        return u'%s' % unicode(self.SegmentType)
    
    class Meta:
        ordering = ['Begin']
        
    def getEnd(self):
        return self.End

class Category(models.Model):
    Label = models.CharField(max_length=10)
    Description = models.CharField(max_length=250)
    CategoryType = models.CharField('Category type',max_length=100)
    
    def isContent(self):
        if self.CategoryType == 'Content':
            return True
        return False
    
    def __unicode__(self):
        return u'%s' % self.Label

class PrevCondProbs(models.Model):
    ActWord = models.ForeignKey('WordType',related_name='prevactword')
    PreviousWord = models.ForeignKey('WordType',related_name='prevword')
    Count = models.IntegerField(blank=True,null=True)
    Prob = models.FloatField(blank=True,null=True)
    
    objects = PCManager()
    
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

class FollCondProbs(models.Model):
    ActWord = models.ForeignKey('WordType',related_name='follactword')
    FollowingWord = models.ForeignKey('WordType',related_name='follword')
    Count = models.IntegerField(blank=True,null=True)
    Prob = models.FloatField(blank=True,null=True)
    
    objects = FCManager()
    
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
    
class WordType(models.Model):
    Label = models.CharField(max_length=250)
    UR = models.ManyToManyField(SegmentType,through=Underlying)
    Count = models.IntegerField(blank=True,null=True)
    Frequency = models.FloatField(blank=True,null=True)
    FreqSource = models.CharField(max_length=100,blank=True,null=True)
    PhonoProb = models.FloatField(blank=True,null=True)
    PhonoSource = models.CharField(max_length=100,blank=True,null=True)
    ND = models.FloatField(blank=True,null=True)
    FWND = models.FloatField(blank=True,null=True)
    CVSkel = models.CharField(max_length=100,blank=True,null=True)
    StressVowel = models.CharField(max_length=10,blank=True,null=True)
    
    def __unicode__(self):
        return u'%s' % self.Label
    
    def getUR(self):
        return ";".join([unicode(s) for s in self.UR.all()])
    
    def getStrUR(self):
        return ' '.join([s.getStrTrans() for s in self.underlying_set.all()])
    
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
        stresses = lookupStress(self.Label, 'IPHOD')
        vows = self.UR.filter(Vowel=True)
        for s in stresses:
            if '1' in s and len(s) == len(vows):
                for i in range(len(vows)):
                    vows[i].Stressed = int(s[i])
                    vows[i].save()
                    if vows[i].Stressed == 1:
                        self.StressVowel = str(vows[i].SegmentType)
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
    
    def getFreq(self):
        if self.Frequency is not None:
            return self.Frequency
        self.Frequency = float(WordToken.objects.filter(WordType=self).count())/float(WordToken.objects.filter(~Q(Category__CategoryType='Other'),~Q(Category__CategoryType='Pause'),~Q(Category__CategoryType='Disfluency')).count())
        self.Frequency = math.log(self.Frequency * 1000000)
        self.FreqSource = 'Buckeye'
        self.save()
        return self.Frequency
    
    def getNDs(self):
        if self.ND is not None and self.FWND is not None:
            return self.ND,self.FWND
        possNeigh = []
        segs = SegmentType.objects.all()
        ur = self.getUR().split(";")
        for i in xrange(len(ur)):
            for j in xrange(len(segs)):
                if ur[i] != segs[j].Label:
                    neigh = ur[:i]
                    neigh.append(segs[j].Label)
                    neigh.extend(ur[i+1:])
                    possNeigh.append(neigh)
            neigh = ur[:i]
            neigh.extend(ur[i+1:])
            possNeigh.append(neigh)
            for j in xrange(len(segs)):
                neigh = ur[:i]
                neigh.append(segs[j].Label)
                neigh.extend(ur[i:])
                possNeigh.append(neigh)
        possNeigh = set([';'.join(x) for x in possNeigh])
        neighCount = 0
        fwnd = 0.0
        words = WordType.objects.filter(~Q(Label__startswith="{"),~Q(Label__startswith="<"))
        for w in words:
            if w.getUR() in possNeigh:
                neighCount += 1
                fwnd += w.getFreq()
        self.ND = neighCount
        self.FWND = fwnd
        self.save()
        return self.ND,self.FWND
    
    def getND(self):
        if self.ND is not None:
            return self.ND
        nd,fwnd = self.getNDs()
        return nd
    
    def getFWND(self):
        if self.FWND is not None:
            return self.FWND
        nd,fwnd = self.getNDs()
        return fwnd
    
    def getPhonoProb(self):
        if self.PhonoProb is None:
            self.setViteLuceProb()
        
        return self.PhonoProb
    
    def setPhonoProb(self,source):
        if source == 'V':
            self.setViteLuceProb()
        elif source == 'B':
            self.PhonoProb = b.assessWord(self.getStrUR())[0]
            self.PhonoSource = 'Blick'
            self.save()
            
                    
    def setViteLuceProb(self):
        SPhoneProb = 0.0
        BiPhoneProb = 0.0
        ur = self.underlying_set.all()
        for s in ur:
            posq = WordType.objects.filter(underlying__Ordering=s.Ordering,underlying__SegmentType=s.SegmentType)
            pos = 0.0
            for p in posq:
                pos += p.getFreq()
            allposq = WordType.objects.filter(underlying__Ordering=s.Ordering)
            allpos = 0.0
            for p in allposq:
                allpos += p.getFreq()
            SPhoneProb += float(pos)/float(allpos)
        if len(ur) > 1:
            for i in xrange(len(ur)-1):
                posq = WordType.objects.filter(underlying__Ordering=ur[i].Ordering,underlying__SegmentType=ur[i].SegmentType).filter(underlying__Ordering=ur[i+1].Ordering,underlying__SegmentType=ur[i+1].SegmentType)
                pos = 0.0
                for p in posq:
                    pos += p.getFreq()
                allposq = WordType.objects.filter(underlying__Ordering=ur[i].Ordering).filter(underlying__Ordering=ur[i+1].Ordering)
                allpos = 0.0
                for p in allposq:
                    allpos += p.getFreq()
                BiPhoneProb += float(pos)/float(allpos)
        self.PhonoProb = (SPhoneProb+BiPhoneProb) / 2.0
        self.Source = 'ViteLuce'
        self.save()
        
#    def getSPhoneProb(self):
#        if self.SPhoneProb is not None:
#            return self.SPhoneProb
#        sp,bp = self.getPhoneProbs()
#        return sp
#    
#    def getBiPhoneProb(self):
#        if self.BiPhoneProb is not None:
#            return self.BiPhoneProb
#        sp,bp = self.getPhoneProbs()
#        return bp
        

class WordToken(models.Model):
    SR = models.ManyToManyField(SegmentType,through=SegmentToken)
    Begin = models.FloatField()
    End = models.FloatField()
    WordType = models.ForeignKey(WordType)
    Category = models.ForeignKey(Category)
    Dialog = models.ForeignKey(Dialog)
    DialogPart = models.CharField(max_length=1)
    StrVowelF1 = models.FloatField(blank=True,null=True)
    StrVowelF2 = models.FloatField(blank=True,null=True)
    SemPred = models.FloatField(blank=True,null=True)
    SynPred = models.FloatField(blank=True,null=True)
    NumFormants = models.DecimalField('Number of formants',max_digits=4,decimal_places=1,blank=True,null=True)
    Ceiling = models.IntegerField(blank=True,null=True)
    
    objects = WTManager()
    
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
    
    def getImmediateSemPred(self):
        context = ['#'.join([str(x),lookupCat(str(x))]) for x in self.getPreviousContext(window=2) if lookupCat(str(x)) in ['n','v','a','r']]
        cat =lookupCat(str(self))
        if cat == 'NA':
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
        sp = getSemanticRelatedness('#'.join([self.WordType.Label,cat]),context)
        return sp
    
    def getSemContext(self):
        if self.SemPred is not None:
            return self.SemPred
        context = ['#'.join([str(x),lookupCat(str(x))]) for x in self.getPreviousContext() if lookupCat(str(x)) in ['n','v','a','r'] and str(x) != str(self)]
        cat =lookupCat(str(self))
        if cat == 'NA':
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
        sp = getSemanticRelatedness('#'.join([self.WordType.Label,cat]),context)
        self.SemPred = sp
        self.save()
        return self.SemPred
    
    def setStrFormants(self,formants=None):
        if formants is not None:
            self.StrVowelF1 = formants[0]
            self.StrVowelF2 = formants[1]
            self.save()
        else:
            path = str(self.Dialog.Speaker) + "/" + str(self.Dialog)+self.DialogPart
            begin,end = self.getStressedVowelInfo()
            ceiling = self.getCeiling()
            nformants = self.getNFormants()
            out = p.getFormants(fetch_media_resource("VIC/Speakers/"+path+'.wav'),begin,end,nformants,ceiling)
            dur = float(end)-float(begin)
            if dur > 0.0:
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
        score,mapping = DTW(map(str,[x.SegmentType for x in ur]),map(str,[x.SegmentType for x in sr]),costs,distOnly=False)
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
        path = fetch_media_resource("VIC/Speakers/"+str(self.Dialog.Speaker) + "/" + str(self.Dialog)+self.DialogPart + ".wav")
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
            prev = WordToken.objects.filter(Dialog=self.Dialog).filter(DialogPart='a').order_by('-Begin')
        else:
            prev = WordToken.objects.filter(Dialog=self.Dialog).filter(End__exact=self.Begin)
        if len(prev) > 0:
            if len(prev) > 1 and prev[0].Category.CategoryType == 'Pause' and prev[0].getDuration() < 0.5:
                return prev[1]
            return prev[0]
        return None

    def getFollowingWord(self):
        foll = WordToken.objects.filter(Dialog=self.Dialog).filter(Begin__exact=self.End)
        if self.DialogPart == 'a' and len(foll) == 0:
            foll = WordToken.objects.filter(Dialog=self.Dialog).filter(DialogPart='b').filter(Begin__exact=0.0)
        if len(foll) > 0:
            if len(foll) > 1 and foll[0].Category.CategoryType == 'Pause' and foll[0].getDuration() < 0.5:
                return foll[1]
            return foll[0]
        return None
    
    def getPreviousContext(self,window=10):
        context = []
        prev = self.getPreviousWord()
        durSum = 0.0
        while durSum < window:
            if prev is None:
                break
            context.append(prev)
            prev = prev.getPreviousWord()
            durSum += self.getDuration()
            if prev is None:
                break
        return reversed(context)

    def getFollowingContext(self):
        folls = []
        f = self.getFollowingWord()
        for i in range(10):
            if f is None:
                break
            folls.append(f)
            f = f.getFollowingWord()
        return folls
    
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
    
    def getNumVows(self):
        numVows = 0
        for seg in self.SR.all():
            if seg.isVowel():
                numVows += 1
        return numVows
    
    def containsNasal(self):
        for seg in self.SR.all():
            if seg.isNasal():
                return True
        return False
    
    def obsCheck(self):
        for s in self.SR.all():
            if not s.isVowel() and not s.isObs():
                return False
        for s in self.WordType.UR.all():
            if not s.isVowel() and not s.isObs():
                return False
        return True
    
    def vowPosCheck(self):
        sr = self.SR.all()
        ur = self.WordType.UR.all()
        if sr[0].isVowel():
            return False
        if sr[sr.count()-1].isVowel():
            return False
        if ur[0].isVowel():
            return False
        if ur[ur.count()-1].isVowel():
            return False
        return True
    
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
        if self.afterPause():
            return 0.0
        prevInd = self.getPreviousWord()
        pauseFound = False
        secsToPause = 0.0
        sylsToPause = 0
        while not pauseFound:
            if prevInd.afterPause():
                pauseFound = True
            secsToPause += prevInd.getDuration()
            sylsToPause += prevInd.getNumSylls()
            prevInd = prevInd.getPreviousWord()
        rate = float(sylsToPause)/float(secsToPause)
        return rate
    
    def getFollowingSpeakingRate(self):
        if self.beforePause():
            return 0.0
        follInd = self.getFollowingWord()
        pauseFound = False
        secsToPause = 0.0
        sylsToPause = 0
        while not pauseFound:
            if follInd.beforePause():
                pauseFound = True
            secsToPause += follInd.getDuration()
            sylsToPause += follInd.getNumSylls()
            follInd = follInd.getFollowingWord()
        rate = float(sylsToPause)/float(secsToPause)
        return rate
    
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
            p.extractToken(filename, beg, end, wavpath)
        if not os.path.isfile(waveformpath):
            p.waveformPic(wavpath,','.join([str(x.End-self.Begin) for x in self.segmenttoken_set.all()]))
            im = Image.open(wfepspath)
            im.save(waveformpath)
            os.remove(wfepspath)
        p.spectroPic(wavpath,1,nformants,ceiling,','.join([str(x.End-self.Begin) for x in self.segmenttoken_set.all()]))
        im = Image.open(specepspath)
        im.save(specpath)
        os.remove(specepspath)
        if not os.path.isfile(outpath):
            p.convertMP3(wavpath)
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
        if self.getNumVows() != 1:
            return False
        if not self.vowPosCheck():
            return False
        return True
    
    def getAnalysisLines(self,form):
        beg,end,vow,prevSound,follSound = self.getAcousticInfo()
        outline = {'Word':self.WordType.Label}
        outline['Vowel'] = self.WordType.getStressVowel()
        outline['PrevCons'] = prevSound
        outline['FollCons'] = follSound
        outline['Token'] = self.pk
        if form['segmentalDurations']:
            outline['VowDur'] = end-beg
            outline['OtherDur'] = self.getDuration()- outline['VowDur']
        if form['speakingRates']:
            outline['PrevSpeakRate'] = self.getPreviousSpeakingRate()
            outline['FollSpeakRate'] = self.getFollowingSpeakingRate()
        if form['contextProbs']:
            outline['PrevCondProb'] = self.getPreviousCondProb()
            outline['FollCondProb'] = self.getFollowingCondProb()
        if form['repetitions']:
            outline['Repetitions'] = self.getRepetitions()
            outline['wasRepeatedRecently'] = self.getRecentRepetition()
        if form['wasRepeated']:
            if 'Repetitions' in outline:
                if outline['Repetitions'] != 0:
                    outline['wasRepeated'] = 'True'
                else:
                    outline['wasRepeated'] = 'False'
            else:
                if self.getRepetitions() != 0:
                    outline['wasRepeated'] = 'True'
                else:
                    outline['wasRepeated'] = 'False'
        if form['category'] == 'B':
            outline['Category'] = self.Category.Label
        elif form['category'] == 'C':
            outline['Category'] = lookupCat(self.WordType.Label)
        elif form['category'] == 'I':
            #outline['Category'] = lookupCategory(self.WordType.Label,'IPHOD')
            pass
        if form['wordDuration']:
            outline['WordDuration'] = self.getDuration()
            outline['BaselineDur'] = self.WordType.getBaseDuration()
        if form['frequency'] == 'B':
            outline['frequency'] = self.WordType.getFreq()
        elif form['frequency'] == 'C':
            #outline['frequency'] = lookupFreq(self.WordType.Label,'CELEX')
            pass
        elif form['frequency'] == 'I':
            #outline['frequency'] = lookupFreq(self.WordType.Label,'IPHOD')
            pass
        if form['gender']:
            outline['SpeakerGender'] = self.Dialog.Speaker.Gender
        if form['age']:
            outline['SpeakerAge'] = self.Dialog.Speaker.Age
        outline['Speaker'] = str(self.Dialog.Speaker)
        if form['orthoLength']:
            outline['OrthoLength'] = len(self.WordType.Label)
        if form['phonoLength']:
            outline['PhonoLength'] = self.WordType.UR.count()
        if form['nd']:
            outline['NeighDen'],outline['FWND'] = self.WordType.getNDs()
        if form['phonotactic'] == 'V':
            if self.WordType.getPhonoSource() != 'ViteLuce':
                self.WordType.setPhonoProb('V')
        elif form['phonotactic'] == 'B':
            if self.WordType.getPhonoSource() != 'Blick':
                self.WordType.setPhonoProb('B')
        outline['PhonoProb'] = self.WordType.getPhonoProb()
        if form['semPred']:
            outline['SemPred'] = self.getSemContext()
            outline['ImmedSemPred'] = self.getImmediateSemPred()
        if form['placeInDialog']:
            outline['placeInDialog'] = self.getDialogPlace()
        outline['AvgSpeakRate'] = self.Dialog.Speaker.getAvgSpeakingRate()
        if form['measure'] == 'S':
            ceiling = self.getCeiling()
            nformants = self.getNFormants()
            p.getFormants(self.getDialogPath(),beg,end,nformants,ceiling)
            out = p.readPraatOut()
            out = p.formatOutput(out, outline, end-beg,getMid=False)
            return out
        else:
            outline['F1'] = self.getStrF1()
            outline['F2'] = self.getStrF2()
            if form['measure'] == 'D':
                if form['DispersionFromAH']:
                    center = self.Dialog.Speaker.getAHCenter()
                else:
                    center = self.Dialog.Speaker.getCenter()
                outline['Dispersion'] = math.sqrt(math.pow(outline['F1']-center[0],2)+math.pow(outline['F2']-center[1],2))
        return [outline]

class SynSemCase(models.Model):
    verb = models.ForeignKey(WordToken)
    checked = models.NullBooleanField()
    complement = models.CharField(max_length=10,blank=True)
    
    def getNoun(self):
        foll = self.verb.getFollowingWord()
        dets = set(['a','an','the','this','these','those'])
        if foll.WordType.Label not in dets and foll.WordType.Label != '<SIL>':
            return foll
        else:
            return foll.getFollowingWord()
        
    def getInter(self):
        inter = []
        n = self.getNoun()
        f = self.verb.getFollowingWord()
        for i in range(10):
            if f == n:
                return inter
            inter.append(f)
            f = f.getFollowingWord()
            
    
    def getPrev(self):
        prevs = []
        p = self.verb.getPreviousWord()
        for i in range(10):
            if p is None:
                break
            prevs.append(p)
            p = p.getPreviousWord()
        return reversed(prevs)

    def getFoll(self):
        folls = []
        f = self.getNoun().getFollowingWord()
        for i in range(10):
            if f is None:
                break
            folls.append(f)
            f = f.getFollowingWord()
        return folls
