
import os
import re
from PIL import Image
import math
import copy
import pickle
from collections import OrderedDict
from picklefield.fields import PickledObjectField

from django.db import models
from django.conf import settings
from django.db.models import Count,Sum,Q
from django.core.exceptions import ObjectDoesNotExist,MultipleObjectsReturned

#import caching.base

# Create your models here.


from linghelper import minEditDist#,SemanticPredictabilityAnalyzer,perl_get_semantic_predictability
from linghelper.phonetics.vowels import analyze_vowel, extract_vowel,get_speaker_means
from linghelper.phonetics.similarity.envelope import envelope_similarity,calc_envelope
from praatinterface import PraatLoader

from linghelper.phonology.stress import guessStress
#if 'phonostats' in settings.INSTALLED_APPS:
#    from phonostats.utils import getNeighCount,getPhonotacticProb,guessStress

if 'celex' in settings.INSTALLED_APPS:
    from celex.utils import categorize_words,get_lexical_info,lookupCat

if 'mysql' in settings.DATABASES['default']['ENGINE']:
    from .helper import mysql_ur_string_lookup as UR_LOOKUP
    from .helper import mysql_speaker_center as SPEAKER_SQL
else:
    from .helper import pg_ur_string_lookup as UR_LOOKUP
    from .helper import pg_speaker_center as SPEAKER_SQL

from .helper import fetch_buckeye_resource,reorganize,fetch_temp_resource


#SEM_PRED = SemanticPredictabilityAnalyzer(ngram=True,use_idf=True)


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
BAD_WORDS = set(['okay','kinda','w','even','only','really','maybe','being','having','awhile','also','was',
            'is','are','am','a','i','the','and','to','that','of','you','like','in','they','but','so',
            'just','have','my','for','know','think','do','on','or','mean','not','be','with','because',
            'well','what','all','if','this','out','at','get','about','them','go','when','me','she',
            'one','then','had','as','up','would','right','lot','no','more','got','were','can','some','things',
            'said','now','something','from','your','him','say','been','where','gonna','see','their','thing',
            'how','here','her','much','kind','two','an','too','did','his','could','has','those','doing',
            'who','these','our','than','into','everything','which','any','anything','three','never','by',
            'why','five','should','off','through','will','whatever','wanna','us','every','done','guess','sure',
            'does','four','might','ten','hum','six','once','either','eight','both','ah','o','d','myself','u',
            'ones','seven','huh','s','nine','few','thousand','anybody','somebody','everybody','hafta','someone',
            'yep','hey','anymore','kinda','seventy','yet','against','anyway','forty','ninety','wow','gotta',
            'such','somewhere','may','bush','gore','there','very','back','ever','q','x','ex','yes','ted',
            'mike','Adam','whatsoever','whatnot','wadi','ups','twos','twenty-one','p','r','l',
            'b','c','e','g','h','j','k','K','m','n','p','t','v','y','z','ag','al','aw','bo','bs',
            'co','da','ec','ed','eh','el','em','er','ew','ha','hi','hm','ho','hu','ih','la','lo',
            'mm','ok','ow','se','th','ya','alabama','africa','african','akron','alaska','albany',
            'america','american','americans','anzio','arab','archie','arlington','asian','ashland'
            ,'athens','atlanta','australia','august','bavarians','belgium','bernice','bethel',
            'boston','bradley','broadway','bruge','buffalo','california','canada','carolina',
            'catholic','catholics','chicago','chinese','christ','christian','bible','christianity'
            ,'christians','christmas','christopher','cincinnati','cleveland','clinton',
            'clintonville','coleman','colin','colorado','columbine','columbus','cuba','dallas',
            'dayton','december','delaware','democrat','democrats','detroit','devon','disney',
            'dorothy','ohio','york','sunday','english','worthington','french','sixteen','florida',
            'vietnam','sixth','northland','eleven','twenty','dublin','eighth','republican',
            'fifth','england','ninth','sixty','german','bob','eew','ann','amy','aha','etc','iis',
            'hmm','meg','ooh','lee','ima','lan','las','los','lou','med','nah','mrs','mhm','phd',
            'san','tom','taj','ugh','yay','yuk','yup','ymca','ural','unix','rosa','pisa','rome',
            'pope','nike','neil','palo','penn','miha','mary','mark','luke','lisa','levy','lima',
            'kirk','kira','kong','kent','karl','june','july','john','joey','jedi','jedd','izod',
            'jack','jane','iowa','iuka','hyde','hong','hers','greg','gosh','fred','eyor','earl',
            'drew','dodd','cosi','coca','cola','cher','byrd','cahs','bing','alta','alps','asia',
            'arlo','ames','yours','ynkow','yadda','xerox','wolff','whoom','wayne','vader','useta',
            'uh-oh','texas','tammy','teddy','tahoe','spitz','spiel','spain','sorta','smith',
            'shawn','sears','scott','satan','sarah','santa','sammy','sally','rosie','roman',
            'roger','robin','riker','reese','Ralph','rabin','qwest','posi-','pixar','peter','paris',
            'peggy','padre','orrin','omaha','nikes','nixon','nancy','miami','megan','mahal','makee',
            'louis','lotta','lordy','logan','linux','linda','legos','kawai','kathy','julie','joyce',
            'jason','jesus','jesse','jerry','james','janet','janie','japan','italy','islam','irish',
            'jacob','ixnay','india','idaho','hyatt','howdy','harry','hasta','hayes','gorka','frank',
            'flint','floyd','exper','emory','elian','ellen','elvis','derek','darth','david','danny',
            'devon','doody','czech','croix','Daddy','daisy','daffy','colin','chris','china',
            'carol','byrds','bronx','bravo','bobby','bingo','betty','amish','toledo','tulsan',
            'venice','vienna','winnie','thomas','theirs','teater','tamara','taylor','tarzan',
            'sydney','smyrna','shuman','senate','russia','sarcom','scioto','schott','ruston',
            'romaro','rommel','robbie','rhodes','reggae','orwell','oregon','oxleys','newark',
            'munich','naples','myrtle','mulder','muchos','mozart','moscow','morris','mormon',
            'monica','morley','monday','mexico','Maslow','mccain','marion','lompoc','malone',
            'lennox','lassie','lamaze','keitel','kenyon','joanne','juliet','joseph','johnny',
            'jewish','jessie','jasper','jansen','jalena','jacobs','israel','hum-um','im-ing',
            'hudson','huh-uh','howser','hitler','heston','harold','hawaii','harvey','guthry',
            'grimes','greece','gospel','george','france','french','eurail','faggot','eugene',
            'europe','elyria','edward','easton','easter','dublin','dundee','doogie','denise',
            'dekalb','crosby','cooper','coulda','cirrus','carson','cayman','cancun','brazil',
            'beulah','bexley','bibles','barney','antrum','arnold','x-files','yitzhak','winfrey',
            'wyandot','william','Voyager','walmart','winston','wooster','thurber','tootsie',
            'tuesday','theresa','sudeten','stergle','stooges','spanish','spandex','solaris',
            'sixties','sixteen','slurpie','sinatra','simpson','siberia','siebert','shoulda',
            'schnook','scooney','russian','roberta','rozutti','pokedex','pokemon','polaris',
            'paterno','ohioian','oberlin','orlando','orleans','october','niagra','nirvana',
            'muslims','mormons','montana','merrill','mitzvah','michael','mexican','matthew',
            'mauldin','maynard','madison','lincoln','liebert','lovejoy','leveque','lazarus',
            'kimonos','kenisha','kwaanza','lashuka','kennedy','jamilia','johnnie','judaism',
            'jamaica','january','janeway','janelle','jackson','italian','ireland','indiana',
            'indians','hungary','hoffman','holland','harvard','harriet','heather','georgia',
            'godsake','germany','germans','gahanna','florida','femalee','ephraim','english',
            'fawcett','eneepee','emante','Ellison','Ellimen','detroit','daytona','cosgray',
            'comfest','charlie','buckeye','bristol','british','bradley','beverly','barbara',
            'arizona','antioch','anthony','anorism','atlanta','amherst','whitesox','wesleyan',
            'victoria','vietcong','themself','stanford','simpsons','samantha','salvador',
            'russians','richmond','richland','richards','rochelle','rockwell','pentagon',
            'portland','murfield','oklahoma','november','nicholas','netstock','nazareth',
            'nebraska','mongolia','mossberg','michelle','mexicans','mid-ohio','michigan',
            'missouri','mcguffey','mcgovern','maverick','masillon','maryland','mackinaw',
            'lutheran','lewinsky','kruschev','jennifer','japanese','janitrol','honolulu',
            'hilliard','hispanic','hawaiian','galberth','futurama','franklin','florence',
            'february','etcetera','european','egyptian','einstein','Delaware','cuyahoga',
            'davidson','delaware','december','columbus','chanukah','Catholic','c.a.h.s.',
            'canberra','buddhism','budapest','brooklyn','brittany','atlantic','arkansas',
            'zollinger','zimbalist','wyandotte','wisconsin','watergate','wadsworth','vancouver',
            'twizzlers','unitarian','tennessee','skywalker','skinheads','shawshank','september',
            'seventies','seventeen','princeton','pataskala','otterbein','owensboro','orangello',
            'olentagy','mussolini','microsoft','methodist','macintosh','mackenzie','louisiana',
            'lancaster','la-dee-da','krushchev','kaczynski','kilbourne','jefferson','johnstown',
            'indianola','henderson','hillsboro','hilliards','holocaust','halloween','francisco',
            ])
MONOPHTHONGS = ['aa','ae','eh','ey','ih','iy','ow','uh','uw']

class Speaker(models.Model):
    """
    This is the class for speakers in the Buckeye Corpus.

    Speaker-specific traits such as Gender and Age are supplied by the
    corpus manual, and default acoustic parameters can be set (though
    word tokens can override acoustic parameters).

    Speaker specific traits can be calculated over all spoken words, such
    as average speaking rate, centers of the vowel space, and average
    formant frequencies for all vowels.
    """
    Number = models.CharField(max_length=3)
    Gender = models.CharField(max_length=10)
    Age = models.CharField(max_length=10)
    NumFormants = models.DecimalField('Number of formants',max_digits=4,decimal_places=1)
    Ceiling = models.IntegerField()
    F1center = models.FloatField(blank=True,null=True)
    F2center = models.FloatField(blank=True,null=True)
    AvgSpeakingRate = models.FloatField(blank=True,null=True)

    #objects = caching.base.CachingManager()

    def __str__(self):
        return u'%s' % (self.Number,)

    def get_AH_center(self):
        """
        This mehod allows the calculation of the average AH production
        to serve as the center of the vowel space, as in Gahl et al.
        (2012).
        """
        if self.F1center is not None and self.F2center is not None:
            return (self.F1center,self.F2center)
        qs = WordToken.objects.filter(WordType__CVSkel='CVC').filter(WordType__StressVowel='ah').filter(Dialog__Speaker__pk=self.pk)
        totF1 = filter(lambda x: x is not None,[q.get_stress_F1() for q in qs])
        totF2 = filter(lambda x: x is not None,[q.get_stress_F2() for q in qs])
        self.F1center = sum(totF1)/float(len(qs))
        self.F2center = sum(totF2)/float(len(qs))
        self.save()
        return (self.F1center,self.F2center)

    def get_center(self):
        """
        Gets the center of the vowel space using custom SQL to get the
        average formant frequencies per vowel, and average them all
        together to get a single center point for the speaker.
        """
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute(SPEAKER_SQL,[self.pk])
        center = cursor.fetchone()
        return (center[0],center[1])

    def get_avg_speaking_rate(self):
        """
        Calculate the average speaking rate over all spoken words.

        Speaking rate is found by dividing the total number of syllables
        spoken by the total duration of words spoken to give a syllables
        per second measure.
        """
        if self.AvgSpeakingRate is not None:
            return self.AvgSpeakingRate
        words = WordToken.objects.filter(Dialog__Speaker=self).filter(Category__CategoryType__in = ['Content','Function','Function_Content','Function_Function'])
        dur = sum([x.get_duration() for x in words])
        sylls = sum([x.get_syllable_count() for x in words])
        self.AvgSpeakingRate = float(sylls)/float(dur)
        self.save()
        return self.AvgSpeakingRate

    def create_dialogs(self):
        """
        Find and create all dialogs for a speaker from the Buckeye
        Corpus materials
        """
        files= os.listdir(fetch_buckeye_resource("Speakers/"+str(self)))
        dialogs = sorted(set([ f[3:5] for f in files]))
        Dialog.objects.bulk_create([ Dialog(Speaker=self,Number=d) for d in dialogs])

    def measure_vowels(self,pk = 0):
        words = WordToken.objects.select_related('WordType','Dialog','Dialog__Speaker','Category')
        words = words.filter(WordType__Label__regex = r'^[^{<]').filter(Dialog__Speaker=self)
        words = words.filter(Category__CategoryType = 'Content').order_by('pk')
        words = words.filter(pk__gt = pk)
        for w in words:
            try:
                w.set_stress_formants()
            except Exception as e:
                print(w.pk)
                raise(e)

    def get_means_covs(self):
        words = WordToken.objects.select_related('WordType','Dialog','Dialog__Speaker','Category')
        words = words.filter(WordType__Label__regex = r'^[^{<]').filter(Dialog__Speaker=self)
        words = words.filter(Category__CategoryType = 'Content').filter(AcousticInformation__isnull=False)
        measurements = {}
        for w in words:
            vow,foll,prec,begin,end = w.get_stressed_vowel_info()
            if (vow,foll,prec) not in measurements:
                measurements[(vow,foll,prec)] = []
            if 'VDur' not in w.AcousticInformation:
                w.AcousticInformation['VDur'] = end - begin
            measurements[(vow,foll,prec)].append({x: w.AcousticInformation[x] for x in ['F1','F2','B1','B2','VDur']})
        means,covs = get_speaker_means(measurements)
        return means,covs


    def remeasure_vowels(self):
        means,covs = self.get_means_covs()
        words = WordToken.objects.select_related('WordType','Dialog','Dialog__Speaker','Category')
        words = words.filter(WordType__Label__regex = r'^[^{<]').filter(Dialog__Speaker=self)
        words = words.filter(Category__CategoryType = 'Content')
        for w in words:
            w.set_stress_formants(speaker_means=means,speaker_covs=covs)

    def analyze(self,form):
        """
        Omnibus method for acoustically analyzing a speaker's speech.

        This method needs to be generalized more.
        """
        words = WordToken.objects.select_related('WordType','Dialog','Dialog__Speaker')
        words = words.filter(WordType__Label__regex = r'^[^{<]').filter(Dialog__Speaker=self)
        #words = words.exclude(WordType__CVSkel__regex = r'^C*VC*$')
        words = words.exclude(WordType__Label__regex = r"[']")
        words = words.exclude(WordType__Label__in = BAD_WORDS)
        #words = words.filter(WordType__CVSkel='CVC')
        #words = words.filter(WordType__Label__in = GOOD_WORDS)
        #words = words.filter(WordType__StressVowel__in = MONOPHTHONGS)
        allout = []
        print(str(self))
        print("\n")
        print(len(words))
        for w in words:
            #if settings.DEBUG:
            #    print(w.pk)
            if not w.WordType.is_acceptable():
                continue
            if not w.is_acceptable():
                continue
            if str(w.Dialog) == 's2003' or str(w.Dialog) =='s4001':
                continue
            out = w.getAnalysisLines(form)
            if out is None:
                continue
            allout.extend(out)
            #if settings.DEBUG:
            #    print allout[-1]
        return allout

    def load_wordtokens(self):
        for d in Dialog.objects.filter(Speaker = self):
            d.load_wordtokens()

    def get_path(self):
        """
        Get absolute file path to a speaker's resources.
        """
        return fetch_buckeye_resource("Speakers/"+str(self))




class Dialog(models.Model):
    """
    Model that allows for grouping words according the specific place
    they were spoken in
    """
    Speaker = models.ForeignKey(Speaker)
    Number = models.CharField(max_length=10)

    #objects = caching.base.CachingManager()

    def __str__(self):
        return u'%s%s' % (self.Speaker,self.Number)

    def get_total_time(self):
        tokens = self.wordtoken_set.all()
        first_part = tokens.filter(DialogPart = 'a').last()
        time = first_part.End
        last_part = tokens.filter(DialogPart = 'b').last()
        if last_part is not None:
            time += last_part.End
        return time, first_part.End / time

    def get_part_a_duration(self):
        tokens = self.wordtoken_set.filter(DialogPart = 'a').order_by('Begin')
        try:
            return tokens.last().End
        except AttributeError:
            print(self)
            print(tokens.count())
            raise(AttributeError)

    def get_repeated_content_words(self,repetitions = 10):
        ws = WordType.objects.filter(Label__regex = r'^[^{<]')
        ws = ws.filter(wordtoken__Dialog=self).annotate(c = Count('wordtoken__id'))
        ws = ws.filter(c__gte = repetitions)
        return ws

    def similarity_analysis(self):
        ws = self.get_repeated_content_words()
        for w in ws:
            y = []
            tokens = w.wordtoken_set.filter(Dialog=self)
            for i in range(len(tokens)):
                wt = tokens[i]
                closest = None
                best = 0
                wt_path = fetch_temp_resource('buckeye-wt-%d.wav' % wt.pk)
                if not os.path.isfile(wt_path):
                    extract_vowel(wt.get_dialog_path(),wt.Begin,wt.End,wt_path)
                if i == len(tokens)-1:
                    break
                for j in range(i+1,len(tokens)):
                    wt2 = tokens[j]
                    wt2_path = fetch_temp_resource('buckeye-wt-%d.wav' % wt2.pk)
                    if not os.path.isfile(wt2_path):
                        extract_vowel(wt2.get_dialog_path(),wt2.Begin,wt2.End,wt2_path)
                    sim = envelope_similarity(wt_path,wt2_path)
                    dist = -math.log(sim)
                    y.append(dist)
            return y



    def get_word_files(self):
        """
        Load the .words files associated with the dialog (most dialogs
        are multipart due to the size of their associated .wav files).
        """
        files = os.listdir(self.Speaker.get_path())
        word_files = [f for f in files if f[:5] == str(self) and re.search("\.words$",f) is not None]
        return word_files

    def load_wordtypes(self):
        wf = self.get_word_files()
        segs = SegmentType.objects.all()
        segs = { x.Label: x for x in segs}
        for f in wf:
            name = re.sub(".words","",f)
            print(name)
            words = pickle.load(open(os.path.join(fetch_buckeye_resource('Processed'),name+'.txt'),'rb'))
            for word in words:
                wordTypes = WordType.objects.filter(Label=word['Word']).prefetch_related('underlying_set')
                w = None
                if len(wordTypes) != 0:
                    for wType in wordTypes:
                        if wType.is_word() and wType.get_UR() == word['UR']:
                            w = wType
                            break
                        elif not wType.is_word():
                            w = wType
                if w is None:
                    w = WordType.objects.create(Label=word['Word'],Count=0)
                    if w.is_word():
                        uls = []
                        ur = word['UR'].split(";")
                        for i in range(len(ur)):
                            sType = segs[ur[i]]
                            uls.append(Underlying(WordType=w,SegmentType=sType,Ordering=i))
                        Underlying.objects.bulk_create(uls)

    def validate_wordtokens(self):
        wf = self.get_word_files()
        wt = self.wordtoken_set.select_related('WordType','Category').prefetch_related('segmenttoken_set').all()
        for f in wf:
            name = re.sub(".words","",f)
            part = name[-1]
            print(name)
            words = pickle.load(open(os.path.join(fetch_buckeye_resource('Processed'),name+'.txt'),'rb'))
            pwt = wt.filter(DialogPart=part)
            for i in range(len(pwt)):
                if not pwt[i].WordType.is_word():
                    continue
                from_file = words[i]
                not_good = False
                if from_file['Word'] != pwt[i].WordType.Label:
                    print(from_file)
                    print(self)
                    print('word label')
                    print(pwt[i].WordType.Label)
                    print(pwt[i].Begin)
                    raise Exception
                if from_file['Begin'] != pwt[i].Begin:
                    print(from_file)
                    print(self)
                    print('begin')
                    print(pwt[i].WordType.Label)
                    print(pwt[i].Begin)
                    raise Exception
                if from_file['End'] != pwt[i].End:
                    print(from_file)
                    print(self)
                    print('end')
                    print(pwt[i].End)
                    print(pwt[i].WordType.Label)
                    print(pwt[i].Begin)
                    raise Exception
                if from_file['Category'] != pwt[i].Category.Label:
                    print(from_file)
                    print(self)
                    print('category')
                    print(pwt[i].Category.Label)
                    print(pwt[i].WordType.Label)
                    print(pwt[i].Begin)
                    raise Exception
                if pwt[i].WordType.is_word():
                    if from_file['UR'] != pwt[i].WordType.get_UR():
                        print(from_file)
                        print(self)
                        print('UR')
                        print(pwt[i].WordType.get_UR(style='empty'))
                        print(pwt[i].WordType.Label)
                        print(pwt[i].Begin)
                        raise Exception
                    sts = [{'Label': x.SegmentType.Label, 'Begin':x.Begin,'End':x.End} for x in pwt[i].segmenttoken_set.all()]
                    if from_file['Phones'] != sts:
                        print(from_file)
                        print(self)
                        print('SR')
                        print(sts)
                        print(pwt[i].WordType.Label)
                        print(pwt[i].Begin)
                        raise Exception


    def load_wordtokens(self):
        """
        Load in all information for a dialog from the Buckeye Corpus
        materials.
        """
        wf = self.get_word_files()
        segs = SegmentType.objects.all()
        segs = { x.Label: x for x in segs}
        cats = Category.objects.all()
        cats = { x.Label: x for x in cats}
        if self.wordtoken_set.count() > 0:
            return None
        prev = None
        for f in wf:
            name = re.sub(".words","",f)
            print(name)
            words = pickle.load(open(os.path.join(fetch_buckeye_resource('Processed'),name+'.txt'),'rb'))
            for word in words:
                cat = cats[word['Category']]
                wordTypes = WordType.objects.filter(Label=word['Word']).prefetch_related('underlying_set')
                if len(wordTypes) > 1:
                    for wType in wordTypes:
                        if wType.get_UR() == word['UR']:
                            w = wType
                            break
                else:
                    w = wordTypes[0]
                wt =WordToken(Begin=word['Begin'],End=word['End'],WordType=w,Category=cat,Dialog=self,DialogPart=name[-1])
                if prev is not None:
                    wt.PreviousWord = prev
                wt.save()
                if prev is not None:
                    prev.FollowingWord = wt
                    prev.save()
                if w.is_word():
                    sts = []
                    for s in word['Phones']:
                        sType = segs[s['Label']]
                        sts.append(SegmentToken(WordToken=wt,SegmentType = sType,Begin=s['Begin'],End=s['End']))
                    SegmentToken.objects.bulk_create(sts)
                prev = wt



class SegmentType(models.Model):
    """
    Model for capturing phonological information about segments.
    """
    Label = models.CharField(max_length=10)
    Syllabic = models.BooleanField()
    Obstruent = models.BooleanField()
    Nasal = models.BooleanField()
    Vowel = models.BooleanField()

    #objects = caching.base.CachingManager()

    def is_syllabic(self):
        return self.Syllabic

    def is_nasal(self):
        return self.Nasal

    def is_obstruent(self):
        return self.Obstruent

    def is_vowel(self):
        return self.Vowel

    def __str__(self):
        return u'%s' % (self.Label,)

    def get_average_dur(self):
        """
        Calculates the average duration of a given segment across all
        instances in the corpus.
        """
        qs = SegmentToken.objects.filter(SegmentType=self)
        durs = [x.End - x.Begin for x in qs]
        return sum(durs)/float(len(durs))

class Underlying(models.Model):
    """
    Many-to-many relation between words and their underlying/canonical
    segments.

    Contains ordering information and stress values for vowels
    """
    WordType = models.ForeignKey('WordType')
    SegmentType = models.ForeignKey(SegmentType)
    Ordering = models.IntegerField()
    Stressed = models.IntegerField(blank=True,null=True)

    #objects = caching.base.CachingManager()

    def __str__(self):
        return str(self.SegmentType)

    def get_stress_trans(self):
        """
        Convert the transcription to include stress notation
        (if applicable).
        """
        if self.Stressed is None:
            return str(self.SegmentType).upper()
        return str(self.SegmentType).upper()+str(self.Stressed)

    class Meta:
        ordering = ['Ordering']

class SegmentToken(models.Model):
    """
    Model for surface realizations of words.
    """
    WordToken = models.ForeignKey('WordToken')
    SegmentType = models.ForeignKey(SegmentType)
    Begin = models.FloatField()
    End = models.FloatField()
    Stressed = models.NullBooleanField()

    #objects = caching.base.CachingManager()

    def __str__(self):
        return str(self.SegmentType)

    class Meta:
        ordering = ['Begin']

    def get_end(self):
        return self.End

    def get_preceding_segment(self,word_internal=True):
        if word_internal:
            qs = self.WordToken.segmenttoken_set.select_related('WordToken','SegmentType').filter(Begin__lt = self.Begin).order_by('-Begin').first()
            return qs
        try:
            qs = SegmentToken.objects.filter(
                        WordToken__Dialog=self.WordToken.Dialog
                        ).filter(WordToken__DialogPart=self.WordToken.DialogPart
                        ).get(End = self.Begin)
        except ObjectDoesNotExist:
            qs = None
        #except MultipleObjectsReturned:
        #    qs = SegmentToken.objects.filter(End = self.Begin).first()
        return qs

    def get_following_segment(self,word_internal=True):
        if word_internal:
            qs = self.WordToken.segmenttoken_set.select_related('WordToken','SegmentType').filter(Begin__gt = self.Begin).first()
            return qs
        try:
            qs = SegmentToken.objects.filter(
                        WordToken__Dialog=self.WordToken.Dialog
                        ).filter(WordToken__DialogPart=self.WordToken.DialogPart
                        ).get(Begin = self.End)
        except ObjectDoesNotExist:
            qs = None
        #except MultipleObjectsReturned:
        #    qs = SegmentToken.objects.filter(Begin = self.End).first()
        return qs


class Category(models.Model):
    """
    Syntactic parts of speech for a given word token, as listed in the
    Buckeye Corpus materials.

    Should probably be redone at some point.  Part of speech tagging
    for spontaneous speech is difficult.
    """
    Label = models.CharField(max_length=10)
    Description = models.CharField(max_length=250)
    CategoryType = models.CharField('Category type',max_length=100)

    #objects = caching.base.CachingManager()

    def is_content(self):
        """
        Content (open class categories) versus function words and other
        tags used.
        """
        if self.CategoryType == 'Content':
            return True
        return False

    def __str__(self):
        return u'%s' % self.Label

class PrevCondProbs(models.Model):
    """
    Model for storing bigram probabilities for a word given its
    preceding word.
    """
    ActWord = models.ForeignKey('WordType',related_name='prevactword')
    PreviousWord = models.ForeignKey('WordType',related_name='prevword')
    Count = models.IntegerField(blank=True,null=True)
    Prob = models.FloatField(blank=True,null=True)

    #objects = caching.base.CachingManager()

    def get_prob(self):
        """
        Calculate conditional probability of word given previous word
        if not already stored.
        """
        if self.Prob is not None:
            return self.Prob
        qs = WordToken.objects.select_related('WordType','PreviousWord').filter(WordType=self.ActWord)
        self.Count = qs.filter(PreviousWord__WordType = self.PreviousWord).count()
        self.Prob = float(self.Count) / float(self.PreviousWord.get_count())
        self.save()
        return self.Prob

class FollCondProbs(models.Model):
    """
    Model for storing bigram probabilities for a word given its
    following word.
    """
    ActWord = models.ForeignKey('WordType',related_name='follactword')
    FollowingWord = models.ForeignKey('WordType',related_name='follword')
    Count = models.IntegerField(blank=True,null=True)
    Prob = models.FloatField(blank=True,null=True)

    #objects = caching.base.CachingManager()

    def get_prob(self):
        """
        Calculate conditional probability of word given following word
        if not already stored.
        """
        if self.Prob is not None:
            return self.Prob
        qs = WordToken.objects.select_related('WordType','FollowingWord').filter(WordType=self.ActWord)
        self.Count = qs.filter(FollowingWord__WordType = self.FollowingWord).count()
        self.Prob = float(self.Count) / float(self.FollowingWord.get_count())
        self.save()
        return self.Prob

class WordType(models.Model):
    """
    Model for storing lexical information about word types in the corpus.

    Word types are more similar to word forms in CELEX than lemmas.

    No morphological information or lemma information which might be nice.
    """
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
    Extra = PickledObjectField(null=True)

    #objects = caching.base.CachingManager()

    def get_celex_info(self):
        """
        Look up and store lexical information from CELEX.
        """
        if self.Extra is None:
            self.Extra = {}
        if 'CelexCategory' not in self.Extra:
            info = get_lexical_info(self.Label)
            try:
                self.Extra['CelexCategory'] = info['Cat']
            except KeyError:
                self.Extra['CelexCategory'] = 'NA'
            try:
                self.Extra['CelexFrequency'] = info['Freq']
            except KeyError:
                self.Extra['CelexFrequency'] = 'NA'
            try:
                self.Extra['CelexNeighDen'],self.Extra['CelexFWND'] = info['ND'], info['FWND']
            except KeyError:
                self.Extra['CelexNeighDen'],self.Extra['CelexFWND'] = 'NA','NA'
            try:
                self.Extra['CelexSPhoneProb'],self.Extra['CelexBiPhoneProb'] = info['SP'],info['BP']
            except KeyError:
                self.Extra['CelexSPhoneProb'],self.Extra['CelexBiPhoneProb'] = 'NA','NA'
            self.save()
        return self.Extra

    def __str__(self):
        return u'%s' % self.Label

    def is_acceptable(self):
        """
        Analyze only contentful words according to CELEX.
        """
        if self.Extra is None or 'CelexCategory' not in self.Extra:
            self.get_celex_info()
        if self.Extra['CelexCategory'] not in ['N','V','ADV','A']:
            return False
        #if self.get_syllable_count() < 2:
        #    return False
        return True

    def get_UR(self,stressed=False,style='buckeye'):
        """
        Get the underlying representation for a word type, can include
        stress information, and be modified to fit the style for BLICK
        (CMU dictionary).
        """

        if style == 'blick':
            t = ' '.join([s.get_stress_trans() for s in self.underlying_set.all()])
            t = re.sub(r'EL(\d?)',r'AH\1 L',t)
            t = re.sub(r'EN(\d?)',r'AH\1 N',t)
            t = re.sub(r'EM(\d?)',r'AH\1 M',t)
            t = re.sub(r'ENG(\d?)',r'AH\1 NG',t)
            t = re.sub(r'([IEAUO][WYOHAE])N(\d?)',r'\1\2 N',t)
        elif style == 'buckeye':
            t = ';'.join([s.get_stress_trans() for s in self.underlying_set.all()])
            t = t.lower()
        elif style == 'empty':
            stressed = False
            t = ' '.join([s.get_stress_trans() for s in self.underlying_set.all()])
        if not stressed:
            t = re.sub(r'\d',r'',t)
        return t

    def get_base_duration(self):
        """
        Get the sum of the average durations for all segments in the
        canonical production.
        """
        return sum([x.get_average_dur() for x in self.UR.all()])

    def get_stress_vowel(self):
        """
        Get the primary stressed vowel of the word, or figure it out if
        necessary.
        """
        if self.StressVowel is None:
            self.figure_stresses()
        return self.StressVowel

    def has_stress(self):
        if self.StressVowel is not None:
            return True
        return False

    def figure_stresses(self):
        """
        Uses BLICK to figure out the most likely stress pattern for the
        word.

        BLICK's guess method looks up the existence of the string
        in its dictionary and returns that if found, otherwise finds the
        transcription that has the lowest violation of its constraints.
        """
        guessed = guessStress(self.get_UR(style='blick'))
        stresses = re.sub(r'\D',r'',guessed)
        syls = self.underlying_set.filter(SegmentType__Syllabic=True)
        for i in range(len(syls)):
            syls[i].Stressed = int(stresses[i])
            syls[i].save()
            if syls[i].Stressed == 1:
                self.StressVowel = str(syls[i].SegmentType)
                self.save()



    def get_CV_skeleton(self):
        """
        Figure out a word's CV skeleton if not known already.
        """
        if self.CVSkel is not None:
            return self.CVSkel
        cv = ''
        for seg in self.underlying_set.all():
            if seg.SegmentType.is_vowel():
                cv += 'V'
            else:
                cv += 'C'
        self.CVSkel = cv
        self.save()
        return self.CVSkel

    def get_syllable_count(self):
        """
        Calculate the number of syllables in the word.
        """
        return sum([x.is_syllabic() for x in self.underlying_set.all()])

    def is_word(self):
        """
        Check for whether the word is an annotation label or a word.
        """
        if self.Label.startswith("{") or self.Label.startswith("<"):
            return False
        else:
            return True

    def get_count(self):
        if self.Count != 0:
            return self.Count
        self.Count = WordToken.objects.filter(WordType=self).count()
        self.save()
        return self.Count

    def get_frequency(self,subset='all',speaker=None,dialog=None):
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

        Freq = float(base.filter(WordType=self).count())/float(base.exclude(Category__CategoryType__in=['Other','Pause','Disfluency']).count())
        Freq = math.log((Freq * 1000000),10)
        if subset=='all':
            self.Frequency = Freq
            self.save()
        return Freq

    def get_neighbours(self):
        any_segment = '[A-Za-z]{1,2}'
        phones = list(map(str,self.underlying_set.all()))
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
        patt = phones + [any_segment]
        patterns.append('^'+' '.join(patt) +'$')
        neighs = WordType.objects.filter(Label__regex="^[^{<]").exclude(pk=self.pk).extra(
                    where = [UR_LOOKUP],
                    params = ['|'.join(patterns)])
        return neighs


    def get_NDs(self,subset='all',speaker=None,dialog=None):
        if subset == 'all' and self.ND is not None and self.FWND is not None:
            return self.ND,self.FWND
        freqs = [ x.get_frequency(subset=subset,speaker=speaker,dialog=dialog)
                        for x in self.get_neighbours()]
        nd = sum([1 for x in freqs if x > 0])
        fwnd = sum(freqs)
        if subset == 'all':
            self.ND,self.FWND = nd,fwnd
            self.save()
        return nd,fwnd

    def get_ND(self,subset='all',speaker=None,dialog=None):
        if subset == 'all' and self.ND is not None:
            return self.ND
        nd,fwnd = self.get_NDs(subset=subset,speaker=speaker,dialog=dialog)
        return nd

    def get_FWND(self,subset='all',speaker=None,dialog=None):
        if subset == 'all' and self.FWND is not None:
            return self.FWND
        nd,fwnd = self.get_NDs(subset=subset,speaker=speaker,dialog=dialog)
        return fwnd

    def get_phono_prob(self,subset='all',speaker=None,dialog=None):
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


class WordToken(models.Model):
    SR = models.ManyToManyField(SegmentType,through=SegmentToken)
    Begin = models.FloatField()
    End = models.FloatField()
    WordType = models.ForeignKey(WordType)
    Category = models.ForeignKey(Category)
    Dialog = models.ForeignKey(Dialog)
    DialogPart = models.CharField(max_length=1)
    AcousticInformation = PickledObjectField(null=True)
    SemanticInformation = PickledObjectField(null=True)
    CachedOutput = PickledObjectField(null=True)
    PreviousWord = models.ForeignKey('self',related_name = 'previous',blank=True,null=True)
    FollowingWord = models.ForeignKey('self',related_name = 'following',blank=True,null=True)

    #objects = caching.base.CachingManager()

    class Meta:
        ordering = ['Dialog','DialogPart','Begin']

    def __str__(self):
        return u'%s' % str(self.WordType)

    def get_envelope(self):
        #if self.AcousticInformation is None:
        #    self.AcousticInformation = {}
        #if 'Envelope' in self.AcousticInformation:
        #    return self.AcousticInformation['Envelope']
        path = fetch_temp_resource('buckeye-wt-%d.wav' % self.pk)
        if not os.path.isfile(path):
            extract_vowel(self.get_dialog_path(),self.Begin,self.End,path)
        env = calc_envelope(path,num_bands=8)
        #self.AcousticInformation['Envelope'] = env
        #self.save()
        return env #self.AcousticInformation['Envelope']

    def get_sense(self,disambiguate=True):
        if not disambiguate:
            return
        if self.Output is None:
            self.Output = {}
        if disambiguate:
            if 'Wordnet_sense' not in self.Output:
                cat = self.get_category(source='celex',style='wordnet')
                if cat is None:
                    self.Output['Wordnet_sense'] = None
                    self.save()
                    return None
                if not disambiguate:
                    return '.'.join([str(self),cat,'1'])
                prev = ' '.join([str(x) for x in self.get_previous_context(window=10)])
                foll = ' '.join([str(x) for x in self.get_following_context(window=10)])
                self.Output['Wordnet_sense'] = SEM_PRED.disambiguate_sense(str(self),cat,prev,foll,to_string=True)
                self.save()
            return self.Output['Wordnet_sense']
        else:
            if 'Default_Wordnet_sense' not in self.Output:
                cat = self.get_category(source='celex',style='wordnet')
                if cat is None:
                    self.Output['Default_Wordnet_sense'] = None
                else:
                    self.Output['Default_Wordnet_sense'] = '.'.join([str(self),cat,'1'])
                    self.save()
            return self.Output['Default_Wordnet_sense']

    def getPrevSemPred(self,style='A',window='A',disambiguate=True):
        if style == 'A' and window == 'A':
            if self.PrevSemPred is not None:
                return self.PrevSemPred
        if window != 'A':
            prev_context = self.get_previous_context(window = int(window))
        else:
            prev_context = self.get_previous_context()
        prev_context = filter(lambda x: x is not None,[ x.get_sense(disambiguate=disambiguate) for x in prev_context if str(x) != str(self)])
        sense = self.get_sense(disambiguate=disambiguate)
        if sense is None:
            return 'NA'
        sp = perl_get_semantic_predictability(sense.replace('.','#'),map(lambda x: x.replace('.','#'),prev_context))
        #sp = SEM_PRED.get_semantic_predictability(sense,prev_context,style=style)
        if style == 'A' and window == 'A':
            self.PrevSemPred = sp
            self.save()
        return sp

    def getFollSemPred(self,style='A',window='A',disambiguate=True):
        if style == 'A' and window == 'A':
            if self.FollSemPred is not None:
                return self.FollSemPred
        if window != 'A':
            foll_context = self.get_following_context(window = int(window))
        else:
            foll_context = self.get_following_context()
        foll_context = filter(lambda x: x is not None,[ x.get_sense(disambiguate=disambiguate) for x in foll_context if str(x) != str(self)])
        sense = self.get_sense(disambiguate=disambiguate)
        if sense is None:
            return 'NA'
        sp = SEM_PRED.get_semantic_predictability(sense,foll_context,style=style)
        if style == 'A' and window == 'A':
            self.FollSemPred = sp
            self.save()
        return sp

    def set_stress_formants(self, style='fave',
                                speaker_means=None,speaker_covs = None):
        if self.AcousticInformation is None:
            self.AcousticInformation = {}
        if style == 'fave':
            #extract stress vowel wave
            temp_filename = fetch_temp_resource('%d-temp.wav' % self.id)
            vowel, foll_seg, prec_seg, begin, end = self.get_stressed_vowel_info()
            if vowel is None:
                return None
            vdur = end - begin
            if vdur < 0.05:
                return None
            self.AcousticInformation['VDur'] = vdur
            dialog_file = self.get_dialog_path()
            extract_vowel(dialog_file,begin,end,temp_filename)

            formants = analyze_vowel(temp_filename, vowel = vowel,
                                            method = 'mahalanobis',
                                            prec_seg = prec_seg, foll_seg = foll_seg,
                                            speaker_gender = self.Dialog.Speaker.Gender,
                                            means = speaker_means, covs = speaker_covs)
            os.remove(temp_filename)
            self.AcousticInformation.update(formants.get_point_measurement(keys=['F1','F2','F3','B1','B2','B3'],return_dict=True))
            self.AcousticInformation.update(formants.get_DCT('F1',return_dict=True))
            self.AcousticInformation.update(formants.get_DCT('F2',return_dict=True))
            self.AcousticInformation.update(formants.get_DCT('F3',return_dict=True))
            self.save()

        #else:
            #p = PraatLoader(settings.PRAAT_PATH,debug=settings.DEBUG)
            #path = str(self.Dialog.Speaker) + "/" + str(self.Dialog)+self.DialogPart
            #begin,end = self.get_stressed_vowel_info()
            #ceiling = self.get_ceiling()
            #nformants = self.get_number_formants()
            #out = p.get_formants(fetch_buckeye_resource("Speakers/"+path+'.wav'),begin,end,nformants,ceiling)
            #dur = float(end)-float(begin)
            #if dur > 0.0 and len(out) > 0:
                #fones = [x['F1(Hz)'] for x in out if x['F1(Hz)'] != '--undefined--' and float(x['time(s)'])/dur> 0.25 and float(x['time(s)'])/dur < 0.75]
                #ftwos = [x['F2(Hz)'] for x in out if x['F2(Hz)'] != '--undefined--' and float(x['time(s)'])/dur> 0.25 and float(x['time(s)'])/dur < 0.75]
                #if len(fones) > 0 and len(ftwos) > 0:
                    #self.StrVowelF1 = sum(map(float,fones))/float(len(fones))
                    #self.StrVowelF2 = sum(map(float,ftwos))/float(len(ftwos))
                    #self.save()

    def has_stress(self):
        for s in self.segmenttoken_set.all():
            if s.Stressed:
                return True
        return False


    def get_SR(self,style = 'empty'):
        if style == 'empty':
            t = " ".join([str(s) for s in self.segmenttoken_set.all()])
        elif style == 'buckeye':
            t = ";".join([str(s) for s in self.segmenttoken_set.all()])
        return t

    def get_stressed_vowel_info(self,no_hiatus=False,word_internal=False):
        if self.has_stress():
            qs = self.segmenttoken_set.get(Stressed=True)
            beg = qs.Begin
            end = qs.End
            vow = str(qs)
            fqs = qs.get_following_segment(word_internal=word_internal)
            if fqs is None:
                foll_seg = ''
            #    return None, None, None, None, None
            else:
                foll_seg = str(fqs)
            pqs = qs.get_preceding_segment(word_internal=word_internal)
            if pqs is None:
                prec_seg = ''
            #    return None, None, None, None, None
            else:
                prec_seg = str(pqs)
            #print(self)
            #print(vow,foll_seg,prec_seg)
            #Fix rhotics
            if vow == 'r' and pqs is not None and pqs.SegmentType.is_vowel() \
                        and pqs.WordToken == qs.WordToken:
                foll_seg = vow
                vow = prec_seg
                beg = pqs.Begin
                end = pqs.End
                qs = pqs
                pqs = pqs.get_preceding_segment()
                if pqs is None:
                    prec_seg = ''
                else:
                    prec_seg = str(pqs)

            elif vow == 'r' and (pqs is None or not pqs.SegmentType.is_vowel()) \
                        and (fqs is None or not fqs.SegmentType.is_vowel()):
                vow = 'er'
            #print(vow,foll_seg,prec_seg)
            if not qs.SegmentType.is_vowel():
                return None, None, None, None, None
            if no_hiatus:
                if fqs is None or fqs.SegmentType.is_vowel():
                    return None, None, None, None, None
                if pqs is None or pqs.SegmentType.is_vowel():
                    return None, None, None, None, None
            return vow,foll_seg,prec_seg,beg,end
        if not self.WordType.has_stress():
            self.WordType.figure_stresses()
        ur = self.WordType.underlying_set.all()
        sr = self.segmenttoken_set.all()
        score,mapping = minEditDist(map(str,[x.SegmentType for x in ur]),map(str,[x.SegmentType for x in sr]),distOnly=False)
        #print(ur)
        #print(sr)
        #print(mapping)
        ui = 0
        sj = 0
        for m in mapping:
            if ui < len(ur)-1 and m[0] == str(ur[ui]):
                if m[1] != '.' and ur[ui].Stressed == 1:

                    sr[sj].Stressed = True
                    sr[sj].save()
                ui += 1
            if sj < len(sr)-1 and m[1] == str(sr[sj]):
                sj += 1
        if not self.has_stress():
            return None, None,None,None,None
        return self.get_stressed_vowel_info()

    def get_dialog_path(self):
        path = fetch_buckeye_resource("Speakers/"+str(self.Dialog.Speaker) + "/" + str(self.Dialog)+self.DialogPart + ".wav")
        return path

    def get_previous_word(self):
        return self.PreviousWord
        #if self.DialogPart == 'b' and self.Begin == 0.0:
            #prev = WordToken.objects.select_related('Category','WordType').filter(Dialog=self.Dialog).filter(DialogPart='a').order_by('-Begin')
        #else:
            #prev = WordToken.objects.select_related('Category','WordType').filter(Dialog=self.Dialog).filter(End__lt=self.End).order_by('-Begin')
        #t = prev.first()
        #if t is not None and t.Category.Label == 'SIL' and t.get_duration() < 0.5:
            #return prev[1]
        #return t

    def get_following_word(self):
        return self.FollowingWord
        #foll = WordToken.objects.select_related('Category','WordType').filter(Dialog=self.Dialog).filter(Begin__gt=self.Begin)
        #if self.DialogPart == 'a' and len(foll) == 0:
            #foll = WordToken.objects.select_related('Category','WordType').filter(Dialog=self.Dialog).filter(DialogPart='b').filter(Begin__exact=0.0)
        #t = foll.first()
        #if t is not None and t.Category.Label == 'SIL' and t.get_duration() < 0.5:
            #return foll[1]
        #return t

    def get_previous_context(self,window='auto'):
        if window == 'auto':
            window_max = 10
        else:
            window_max = window
        min_val = self.Begin-window_max
        context = WordToken.objects.select_related('Category','WordType')
        context = context.filter(Dialog=self.Dialog).filter(DialogPart=self.DialogPart)
        context = context.filter(End__lt=self.End)
        context = context.filter(Begin__gte = min_val).order_by('-Begin')
        prev_context = []
        for w in context:
            if not w.WordType.is_word():
                if w.Category.CategoryType == 'Pause' and w.get_duration() < 0.5:
                    continue
                else:
                    break
            prev_context.append(w)
        return list(reversed(prev_context))

    def get_following_context(self,window='auto'):
        if window == 'auto':
            window_max = 10
        else:
            window_max = window
        min_val = self.Begin+window_max
        context = WordToken.objects.select_related('Category','WordType')
        context = context.filter(Dialog=self.Dialog).filter(DialogPart=self.DialogPart)
        context = context.filter(End__gt=self.End)
        context = context.filter(Begin__lte = min_val).order_by('Begin')
        foll_context = []
        for w in context:
            if not w.WordType.is_word():
                if w.Category.CategoryType == 'Pause' and w.get_duration() < 0.5:
                    continue
                else:
                    break
            foll_context.append(w)
        return foll_context

    def get_recent_repetition(self):
        cont = set(map(str,self.get_previous_context()))
        if str(self) in cont:
            return True
        return False

    def get_repetitions(self):
        reps = WordToken.objects.filter(Dialog=self.Dialog).filter(DialogPart=self.DialogPart).filter(End__lte=self.Begin).filter(WordType=self.WordType).count()
        if self.DialogPart == 'b':
            reps = reps + WordToken.objects.filter(Dialog=self.Dialog).filter(DialogPart='a').filter(WordType=self.WordType).count()
        return reps

    def get_dialog_place(self):
        diagPlace = self.Begin
        if self.DialogPart == 'b':
            lengthOfA = self.Dialog.get_part_a_duration()
            diagPlace += lengthOfA
        return diagPlace

    def get_syllable_count(self):
        return sum([x.is_syllabic() for x in self.SR.all()])

    def get_duration(self):
        return self.End - self.Begin

    def after_pause(self):
        prev = self.get_previous_word()
        if prev is None:
            return True
        if prev.Category.CategoryType == "Disfluency":
            return True
        if prev.Category.CategoryType == "Other":
            return True
        if prev.Category.CategoryType == "Pause":
            if prev.get_duration() >= 0.5:
                return True
        return False

    def before_pause(self):
        foll = self.get_following_word()
        if foll is None:
            return True
        if foll.Category.CategoryType == "Disfluency":
            return True
        if foll.Category.CategoryType == "Other":
            return True
        if foll.Category.CategoryType == "Pause":
            if foll.get_duration() >= 0.5:
                return True
        return False

    def next_to_pause(self):
        if self.after_pause():
            return True
        if self.before_pause():
            return True
        return False

    def get_previous_speaking_rate(self):
        prev_context = self.get_previous_context()
        total_syllables = float(sum([x.get_syllable_count() for x in prev_context]))
        total_seconds = self.get_prev_dist_to_pause()
        if total_seconds != 0.0:
            rate = total_syllables / total_seconds
        else:
            rate = 0.0
        return rate

    def get_following_speaking_rate(self):
        foll_context = self.get_following_context()
        total_syllables = float(sum([x.get_syllable_count() for x in foll_context]))
        total_seconds = self.get_foll_dist_to_pause()
        if total_seconds != 0.0:
            rate = total_syllables / total_seconds
        else:
            rate = 0.0
        return rate

    def get_prev_dist_to_pause(self):
        if self.after_pause():
            return 0.0
        return sum([x.get_duration() for x in self.get_previous_context()])

    def get_foll_dist_to_pause(self):
        if self.before_pause():
            return 0.0
        return sum([x.get_duration() for x in self.get_following_context()])

    def get_previous_cond_prob(self):
        if self.after_pause():
            return 0.0
        prev = self.get_previous_word()
        pc = PrevCondProbs.objects.get_or_create(ActWord=self.WordType,PreviousWord=prev.WordType)[0]
        return pc.get_prob()

    def get_following_cond_prob(self):
        if self.before_pause():
            return 0.0
        foll = self.get_following_word()
        fc = FollCondProbs.objects.get_or_create(ActWord=self.WordType,FollowingWord=foll.WordType)[0]
        return fc.get_prob()

    def create_pictures(self):
        p = PraatLoader(settings.PRAAT_PATH,debug=settings.DEBUG)
        wavpath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+".wav")
        outpath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+".mp3")
        specepspath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+"-spectro.eps")
        specpath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+"-spectro.png")
        wfepspath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+"-waveform.eps")
        waveformpath = os.path.join(settings.TEMP_DIR,"Buckeye-"+str(self.pk)+"-waveform.png")
        filename = self.get_dialog_path()
        beg = self.Begin
        end = self.End
        ceiling = self.get_ceiling()
        nformants = self.get_number_formants()
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

    def is_acceptable(self):
        if self.next_to_pause():
            return False
        return True

    def get_category(self,source='celex',style=None):
        if source =='celex':
            cat = self.getCelexCat()
        else:
            cat = str(self.Category)
        if style == 'wordnet':
            if source == 'celex':
                if cat == 'ADV':
                    cat = 'R'

                if cat not in ['N','A','R','V']:
                    return None
                cat = cat.lower()
            else:
                if 'N' in cat:
                    cat = 'n'
                elif 'JJ' in cat:
                    cat = 'a'
                elif 'VB' in cat:
                    cat = 'v'
                elif 'RB' in cat:
                    cat = 'r'
                else:
                    return None
        return cat

    def getCelexCat(self):
        if self.Output is None:
            self.Output = {}
        if 'CelexCategory' not in self.Output:
            cat = self.WordType.get_celex_info()['CelexCategory']
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

        if 'Word' not in outline:
            outline['Word'] = self.WordType.Label
        if 'Token' not in outline:
            outline['Token'] = self.pk
        if 'Speaker' not in outline:
            outline['Speaker'] = str(self.Dialog.Speaker)

        if form['measure'] != 'N':
            beg,end,vow,prevSound,follSound = self.get_acoustic_info()
            if 'Vowel' not in outline:
                outline['Vowel'] = self.WordType.get_stress_vowel()
                outline['PrevCons'] = prevSound
                outline['FollCons'] = follSound
            if form['segmentalDurations']:
                if 'VowDur' not in outline:
                    outline['VowDur'] = end-beg
                    outline['OtherDur'] = self.get_duration()- outline['VowDur']
        if form['speakingRates']:
            if 'PrevSpeakRate' not in outline:
                outline['PrevSpeakRate'] = self.get_previous_speaking_rate()
                outline['FollSpeakRate'] = self.get_following_speaking_rate()
                outline['AvgSpeakRate'] = self.Dialog.Speaker.get_avg_speaking_rate()
        if form['contextProbs']:
            if 'PrevCondProb' not in outline:
                outline['PrevCondProb'] = self.get_previous_cond_prob()
                outline['FollCondProb'] = self.get_following_cond_prob()
        if form['repetitions']:
            if 'Repetitions' not in outline:
                outline['Repetitions'] = self.get_repetitions()
                outline['wasRepeatedRecently'] = self.get_recent_repetition()
        if form['wasRepeated']:
            if 'Repetitions' not in outline:
                outline['Repetitions'] = self.get_repetitions()
            if 'wasRepeated' not in outline:
                if outline['Repetitions'] != 0:
                    outline['wasRepeated'] = 'True'
                else:
                    outline['wasRepeated'] = 'False'
        celex_info = self.WordType.get_celex_info()
        if 'CelexCategory' not in outline:
            outline['CelexCategory'] = celex_info['CelexCategory']

        if 'B' in form['category']:
            if 'BuckeyeCategory' not in outline:
                outline['BuckeyeCategory'] = self.Category.Label

        if form['wordDuration']:
            if 'WordDuration' not in outline:
                outline['WordDuration'] = self.get_duration()
                outline['BaselineDur'] = self.WordType.get_base_duration()

        if form['frequency']:
            if 'C' in form['lexical_scale'] and 'CelexFrequency' not in outline:
                try:
                    outline['CelexFrequency'] = celex_info['CelexFrequency']
                except KeyError:
                    outline['CelexFrequency'] = 'NA'
            if 'W' in form['lexical_scale'] and 'BuckeyeFrequency' not in outline:
                outline['BuckeyeFrequency'] = self.WordType.get_frequency()
            if 'S' in form['lexical_scale'] and 'SpeakerFrequency' not in outline:
                outline['SpeakerFrequency'] = self.WordType.get_frequency(subset='speaker',speaker=self.Dialog.Speaker)
            if 'A' in form['lexical_scale'] and 'AgeFrequency' not in outline:
                outline['AgeFrequency'] = self.WordType.get_frequency(subset='age',speaker=self.Dialog.Speaker)
            if 'G' in form['lexical_scale'] and 'GenderFrequency' not in outline:
                outline['GenderFrequency'] = self.WordType.get_frequency(subset='gender',speaker=self.Dialog.Speaker)
            if 'D' in form['lexical_scale'] and 'DialogFrequency' not in outline:
                outline['DialogFrequency'] = self.WordType.get_frequency(subset='dialog',speaker=self.Dialog.Speaker,dialog=self.Dialog)

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
                    outline['CelexNeighDen'],outline['CelexFWND'] = celex_info['CelexNeighDen'],celex_info['CelexFWND']
                except KeyError:
                    outline['CelexNeighDen'],outline['CelexFWND'] = 'NA','NA'
            if 'W' in form['lexical_scale'] and 'BuckeyeNeighDen' not in outline:
                outline['BuckeyeNeighDen'],outline['BuckeyeFWND'] = self.WordType.get_NDs()
            if 'S' in form['lexical_scale'] and 'SpeakerNeighDen' not in outline:
                outline['SpeakerNeighDen'],outline['SpeakerFWND'] = self.WordType.get_NDs(subset='speaker',speaker=self.Dialog.Speaker)
            if 'A' in form['lexical_scale'] and 'AgeNeighDen' not in outline:
                outline['AgeNeighDen'],outline['AgeFWND'] = self.WordType.get_NDs(subset='age',speaker=self.Dialog.Speaker)
            if 'G' in form['lexical_scale'] and 'GenderNeighDen' not in outline:
                outline['GenderNeighDen'],outline['GenderFWND'] = self.WordType.get_NDs(subset='gender',speaker=self.Dialog.Speaker)
            if 'D' in form['lexical_scale'] and 'DialogNeighDen' not in outline:
                outline['DialogNeighDen'],outline['DialogFWND'] = self.WordType.get_NDs(subset='dialog',speaker=self.Dialog.Speaker,dialog=self.Dialog)

        if form['phonotactic']:
            if 'C' in form['lexical_scale'] and 'CelexSPhoneProb' not in outline:
                try:
                    outline['CelexSPhoneProb'],outline['CelexBiPhoneProb'] = celex_info['CelexSPhoneProb'],celex_info['CelexBiPhoneProb']
                except KeyError:
                    outline['CelexSPhoneProb'],outline['CelexBiPhoneProb'] = 'NA','NA'
            if 'W' in form['lexical_scale'] and 'BuckeyeSPhoneProb' not in outline:
                outline['BuckeyeSPhoneProb'],outline['BuckeyeBiPhoneProb'] = self.WordType.get_phono_prob()
            if 'S' in form['lexical_scale'] and 'SpeakerSPhoneProb' not in outline:
                qs = WordToken.objects.filter(Dialog__Speaker= self.Dialog.Speaker).filter(WordType=self.WordType).order_by('Dialog')
                for q in qs:
                    if q.Output is not None and 'SpeakerSPhoneProb' in q.Output:
                        outline['SpeakerSPhoneProb'],outline['SpeakerBiPhoneProb'] = q.Output['SpeakerSPhoneProb'],q.Output['SpeakerBiPhoneProb']
                        break
                else:
                    outline['SpeakerSPhoneProb'],outline['SpeakerBiPhoneProb'] = self.WordType.get_phono_prob(subset='speaker',speaker=self.Dialog.Speaker)
            if 'A' in form['lexical_scale'] and 'AgeSPhoneProb' not in outline:
                qs = WordToken.objects.filter(Dialog__Speaker__Age= self.Dialog.Speaker.Age).filter(WordType=self.WordType).order_by('Dialog')
                for q in qs:
                    if q.Output is not None and 'AgeSPhoneProb' in q.Output:
                        outline['AgeSPhoneProb'],outline['AgeBiPhoneProb'] = q.Output['AgeSPhoneProb'],q.Output['AgeBiPhoneProb']
                        break
                else:
                    outline['AgeSPhoneProb'],outline['AgeBiPhoneProb'] = self.WordType.get_phono_prob(subset='age',speaker=self.Dialog.Speaker)
            if 'G' in form['lexical_scale'] and 'GenderSPhoneProb' not in outline:
                qs = WordToken.objects.filter(Dialog__Speaker__Gender= self.Dialog.Speaker.Gender).filter(WordType=self.WordType).order_by('Dialog')
                for q in qs:
                    if q.Output is not None and 'GenderSPhoneProb' in q.Output:
                        outline['GenderSPhoneProb'],outline['GenderBiPhoneProb'] = q.Output['GenderSPhoneProb'],q.Output['GenderBiPhoneProb']
                        break
                else:
                    outline['GenderSPhoneProb'],outline['GenderBiPhoneProb'] = self.WordType.get_phono_prob(subset='gender',speaker=self.Dialog.Speaker)
            if 'D' in form['lexical_scale'] and 'DialogSPhoneProb' not in outline:
                outline['DialogSPhoneProb'],outline['DialogBiPhoneProb'] = self.WordType.get_phono_prob(subset='dialog',speaker=self.Dialog.Speaker,dialog=self.Dialog)

        if form['additional_phono_stats']:
            if 'PhonoStatsNeighDen' not in outline:
                outline['PhonoStatsNeighDen'] = getNeighCount(self.WordType.get_UR(
                                                        stressed=True,style='blick'),no_stress=True)
            if 'PhonoStatsBlickPhono' not in outline:
                outline['PhonoStatsBlickPhono'] = getPhonotacticProb(self.WordType.get_UR(
                                                        stressed=True,style='blick'),
                                                        use_blick=True,no_stress=True)
            if 'PhonoStatsSPhoneProb' not in outline:
                outline['PhonoStatsSPhoneProb'],outline['PhonoStatsBiPhoneProb'] = getPhonotacticProb(self.WordType.get_UR(
                                                        stressed=True,style='blick'),use_blick=False,no_stress=True)

        for w in eval(form['sem_pred_window']):
            for s in eval(form['sem_pred_style']):
                for d in eval(form['sense_options']):
                    if d == 'Disambiguate':
                        dcheck = True
                    else:
                        dcheck = False
                    if form['prev_sem_pred']:
                        label = '%s%sWindowPrev%sSemPred' %(d,w,s)
                        if label not in outline:
                            outline[label] = self.getPrevSemPred(window = w,style=s,disambiguate=dcheck)
                    if form['foll_sem_pred']:
                        label = '%s%sWindowFoll%sSemPred' %(d,w,s)
                        if label not in outline:
                            outline[label] = self.getFollSemPred(window = w,style=s,disambiguate=ddcheck)
        if form['pause_dist']:
            if 'DistFollPause' not in outline:
                outline['DistFollPause'] = self.get_foll_dist_to_pause()
            if 'DistPrevPause' not in outline:
                outline['DistPrevPause'] = self.get_prev_dist_to_pause()
        if form['placeInDialog']:
            if 'placeInDialog' not in outline:
                outline['placeInDialog'] = self.get_dialog_place()
        if form['measure'] == 'S':
            if 'formants' not in outline:
                ceiling = self.get_ceiling()
                nformants = self.get_number_formants()
                outline['formants'] = [ {'time(s)':x['time(s)'],
                            'F1(Hz)':x['F1(Hz)'],
                            'F2(Hz)':x['F2(Hz)']}
                            for x in p.get_formants(self.get_dialog_path(),beg,end,nformants,ceiling)
                                if x['F1(Hz)'] != '--undefined--' and x['F2(Hz)'] != '--undefined--']
            to_out = [ {'time':x['time(s)'],
                            'F1':x['F1(Hz)'],
                            'F2':x['F2(Hz)']}.update({k:outline[k] for k in outline
                                                            if k != 'formants' and k in wanted_fields})
                            for x in outline['formants']]
        elif form['measure'] != 'N':
            if 'F1' not in outline:
                F1 = self.get_stress_F1()
                F2 = self.get_stress_F2()
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
                        center = self.Dialog.Speaker.get_AH_center()
                        outline['AHDispersion'] = math.sqrt(math.pow(outline['F1']-center[0],2)+math.pow(outline['F2']-center[1],2))

                else:
                    if 'Dispersion' not in outline:
                        center = self.Dialog.Speaker.get_center()
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
        if self.WordType.is_word():
            sp,bp = self.WordType.get_phono_prob()
            cont = OrderedDict([('Previous conditional probability', self.get_previous_cond_prob()),
                        ('Following conditional probability', self.get_following_cond_prob()),
                        ('Previous speaking rate', self.get_previous_speaking_rate()),
                        ('Following speaking rate', self.get_following_speaking_rate()),
                        ('Previous distance to pause', self.get_prev_dist_to_pause()),
                        ('Following distance to pause', self.get_foll_dist_to_pause()),
                        ('Previous semantic predictability', self.get_prev_sem_pred()),
                        ('Following semantic predictability',self.get_foll_sem_pred())])
            lex = OrderedDict([('Word', str(self.WordType)),
                            ('Underlying representation', self.WordType.get_UR()),
                            ('Buckeye frequency', self.WordType.get_frequency()),
                            ('Buckeye single-phone probability', sp),
                            ('Buckeye bi-phone probability', bp),
                            ('Buckeye neighbourhood density', self.WordType.get_ND()),
                            ('Buckeye frequency-weighted neighbourhood density', self.WordType.get_FWND()),
                            ('Stress vowel', self.WordType.get_stress_vowel())])
            tok = OrderedDict([('Dialog', str(self.Dialog)),
                            ('Surface representation', self.get_SR()),
                            ('Buckeye category', str(self.Category)),
                            ('Stress vowel F1', self.get_stress_F1()),
                            ('Stress vowel F2', self.get_stress_F2()),
                            ('Repetitions', self.get_repetitions()),
                            ('Given', self.get_recent_repetition())])
            speak = OrderedDict([('Speaker', str(self.Dialog.Speaker)),
                            ('Gender', self.Dialog.Speaker.Gender),
                            ('Age', self.Dialog.Speaker.Age),
                            ('Number of formants', self.Dialog.Speaker.NumFormants),
                            ('Formant ceiling', self.Dialog.Speaker.Ceiling),
                            ('Vowel center', self.Dialog.Speaker.get_center()),
                            ('Average speaking rate', self.Dialog.Speaker.get_avg_speaking_rate())])
            out = {'Preceding': self.get_previous_context(),
                    'Following': self.get_following_context(),
                    'Word': str(self.WordType),
                    'NFormants': self.get_number_formants(),
                    'Ceiling': self.get_ceiling(),
                    'TokenID': self.pk,
                    'Contextual': cont,
                    'Lexical':lex,
                    'Token':tok,
                    'Speaker':speak}
        else:
            cont = OrderedDict([('Previous speaking rate', self.get_previous_speaking_rate()),
                        ('Following speaking rate', self.get_following_speaking_rate()),
                        ('Previous distance to pause', self.get_prev_dist_to_pause()),
                        ('Following distance to pause', self.get_foll_dist_to_pause())])
            tok = OrderedDict([('Dialog', str(self.Dialog)),
                            ('Buckeye category', str(self.Category))])
            speak = OrderedDict([('Speaker', str(self.Dialog.Speaker)),
                            ('Gender', self.Dialog.Speaker.Gender),
                            ('Age', self.Dialog.Speaker.Age),
                            ('Number of formants', self.Dialog.Speaker.NumFormants),
                            ('Formant ceiling', self.Dialog.Speaker.Ceiling),
                            ('Vowel center', self.Dialog.Speaker.get_center()),
                            ('Average speaking rate', self.Dialog.Speaker.get_avg_speaking_rate())])
            out = {'Preceding': self.get_previous_context(window=10),
                    'Following': self.get_following_context(window=10),
                    'Word': str(self.WordType),
                    'NFormants': self.Dialog.Speaker.NumFormants,
                    'Ceiling': self.Dialog.Speaker.Ceiling,
                    'TokenID': self.pk,
                    'Contextual':cont,
                'Token':tok,
                'Speaker':speak}

        return out
