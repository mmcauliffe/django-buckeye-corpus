"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase

#from linghelper import DTW,getSemanticRelatedness

from .models import *
from .utils import load_segments_from_file,\
                    load_speakers_from_file,\
                    load_categories_from_file,\
                    reset_database

class BasicBuckeyeTest(TestCase):
    def setUp(self):
        load_segments_from_file()
        load_speakers_from_file()
        load_categories_from_file()
        Speaker.objects.first().create_dialogs()

        self.at = WordType.objects.create(Label='at',Count = 0)
        self.cat = WordType.objects.create(Label='cat',Count = 0)
        self.cut = WordType.objects.create(Label='cut',Count = 0)
        self.cuts = WordType.objects.create(Label='cuts',Count = 0)
        self.dog = WordType.objects.create(Label='dog',Count = 0)

        self.SIL = WordType.objects.create(Label = '<SIL>',Count = 0)
        self.VOCNOISE = WordType.objects.create(Label = '<VOCNOISE>',Count = 0)

        k = SegmentType.objects.get(Label='k')
        ae = SegmentType.objects.get(Label='ae')
        ah = SegmentType.objects.get(Label='ah')
        t = SegmentType.objects.get(Label='t')
        s = SegmentType.objects.get(Label='s')
        d = SegmentType.objects.get(Label='d')
        aa = SegmentType.objects.get(Label='aa')
        g = SegmentType.objects.get(Label='g')
        uls = [
                Underlying(WordType=self.at,SegmentType=ae,Ordering=0),
                Underlying(WordType=self.at,SegmentType=t,Ordering=1),
                Underlying(WordType=self.cat,SegmentType=k,Ordering=0),
                Underlying(WordType=self.cat,SegmentType=ae,Ordering=1),
                Underlying(WordType=self.cat,SegmentType=t,Ordering=2),
                Underlying(WordType=self.cut,SegmentType=k,Ordering=0),
                Underlying(WordType=self.cut,SegmentType=ah,Ordering=1),
                Underlying(WordType=self.cut,SegmentType=t,Ordering=2),
                Underlying(WordType=self.cuts,SegmentType=k,Ordering=0),
                Underlying(WordType=self.cuts,SegmentType=ah,Ordering=1),
                Underlying(WordType=self.cuts,SegmentType=t,Ordering=2),
                Underlying(WordType=self.cuts,SegmentType=s,Ordering=3),
                Underlying(WordType=self.dog,SegmentType=d,Ordering=0),
                Underlying(WordType=self.dog,SegmentType=aa,Ordering=1),
                Underlying(WordType=self.dog,SegmentType=g,Ordering=2),
                ]
        Underlying.objects.bulk_create(uls)
        c = Category.objects.get(Label='NN')
        c2 = Category.objects.get(Label='NOI')
        d = Dialog.objects.first()
        wts = [
                WordToken(WordType=self.at,Begin=0,End=1,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.at,Begin=1,End=2,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.at,Begin=2,End=3,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.at,Begin=3,End=4,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.at,Begin=4,End=5,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.VOCNOISE,Begin=5,End=6,Category=c2,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.cat,Begin=6,End=7,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.cut,Begin=7,End=8,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.cuts,Begin=8,End=9,Category=c,Dialog=d,DialogPart='a'),

                WordToken(WordType=self.VOCNOISE,Begin=9,End=10,Category=c2,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.cat,Begin=10,End=11,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.cut,Begin=11,End=12,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.dog,Begin=12,End=13,Category=c,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.VOCNOISE,Begin=13,End=14,Category=c2,Dialog=d,DialogPart='a'),
                WordToken(WordType=self.cuts,Begin=14,End=15,Category=c,Dialog=d,DialogPart='a'),
                ]
        WordToken.objects.bulk_create(wts)
        prev = None
        tokens = WordToken.objects.all()
        for wt in tokens:
            if prev is not None:
                wt.PreviousWord = prev
                wt.save()
                prev.FollowingWord = wt
                prev.save()
                print(prev.FollowingWord)
            prev = wt
        sts = []
        for i in range(5):
            wt = WordToken.objects.get(Begin=i)
            sts.append(SegmentToken(WordToken = wt, SegmentType= ae,Begin=wt.Begin,End=wt.End))
        SegmentToken.objects.bulk_create(sts)

#class LoadingTest(TestCase):
    #def setUp(self):
        #load_segments_from_file()
        #load_speakers_from_file()
        #load_categories_from_file()
    #def test_load(self):
    #    s = Speaker.objects.get(pk=1)
    #    self.assertEqual(s.pk,1)
    #    s.load_dialogs()
    #def test_reset(self):
    #    reset_database()

class LexicalTest(BasicBuckeyeTest):


    def test_underlying_rep(self):
        self.assertEqual(self.cat.get_UR(),'k;ae;t')

    def test_neighbourhood_density(self):
        self.assertEqual(self.at.get_ND(),1)
        self.assertEqual(self.cat.get_ND(),2)
        self.assertEqual(self.cut.get_ND(),2)
        self.assertEqual(self.cuts.get_ND(),1)
        self.assertEqual(self.dog.get_ND(),0)

    def test_stress_assignment(self):
        self.assertEqual(self.at.get_stress_vowel(), 'ae')
        self.assertEqual(self.cat.get_stress_vowel(), 'ae')
        self.assertEqual(self.cut.get_stress_vowel(), 'ah')
        self.assertEqual(self.cuts.get_stress_vowel(), 'ah')
        self.assertEqual(self.dog.get_stress_vowel(), 'aa')

    def test_cv_skeletons(self):
        self.assertEqual(self.at.get_CV_skeleton(), 'VC')
        self.assertEqual(self.cat.get_CV_skeleton(), 'CVC')
        self.assertEqual(self.cut.get_CV_skeleton(), 'CVC')
        self.assertEqual(self.cuts.get_CV_skeleton(), 'CVCC')
        self.assertEqual(self.dog.get_CV_skeleton(), 'CVC')


    def test_count(self):
        self.assertEqual(self.dog.get_count(),1)
        self.assertEqual(self.cat.get_count(),2)

class TokenTest(BasicBuckeyeTest):
    def test_speaking_rate(self):
        wt = WordToken.objects.get(Begin = 1)
        wt2 = WordToken.objects.get(Begin = 0)

        self.assertEqual(list(wt.get_previous_context()),[wt2])
        self.assertEqual(wt2.get_syllable_count(),1)
        self.assertEqual(wt2.get_duration(),1)
        self.assertEqual(wt.get_previous_speaking_rate(),1)
        self.assertEqual(wt.get_following_speaking_rate(),1)

    def test_previous_following(self):
        wt = WordToken.objects.get(Begin = 7)
        wt2 = WordToken.objects.get(Begin = 8)
        self.assertEqual(wt.get_following_word(),wt2)
        self.assertEqual(wt,wt2.get_previous_word())

    def test_pause_dist(self):
        wt2 = WordToken.objects.get(Begin = 0)
        wt = WordToken.objects.get(Begin = 1)
        self.assertEqual(list(wt.get_previous_context()),[wt2])
        self.assertEqual(list(wt.get_following_context()),list(WordToken.objects.filter(Begin__gt = 1)[:3]))
        self.assertEqual(wt.get_prev_dist_to_pause(),1)
        self.assertEqual(wt.get_foll_dist_to_pause(),3)

    def test_previous_prob(self):
        wt = WordToken.objects.get(Begin = 7)
        self.assertEqual(wt.get_previous_cond_prob(),1)
        self.assertEqual(wt.get_following_cond_prob(),0.5)


    def test_pause_adjacency(self):
        wt = WordToken.objects.get(Begin = 4)
        self.assertTrue(wt.before_pause())
        self.assertTrue(wt.next_to_pause())
        wt = WordToken.objects.get(Begin = 6)
        self.assertTrue(wt.after_pause())
        self.assertTrue(wt.next_to_pause())

#class BuckeyeTest(TestCase):
    #fixtures = ['buckeyebrowser_testdata.json']
    #def test_prev_semantic_predictability(self):
        #word = WordToken.objects.get(pk = 3863)
        #self.assertEqual([str(x) for x in word.getPreviousContext()], ['kind','of','really',
                                                    #"didn't",'get','together',
                                                    #'at','all','freshman'])
        #context = ['kind#n','really#r','get#v','together#r','freshman#n']
        #sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='S')
        #self.assertEqual(sum([48,16,59,13,16]),sp)
        #sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='A')
        #self.assertEqual(float(sum([48,16,59,13,16]))/float(5),sp)

        #self.assertEqual([str(x) for x in word.getPreviousContext(window=10)],
                            #['mom','an','his','mom','were','campfire','leaders',
                            #'together','and','the','whole','bit','and','then',
                            #'we','didn\'t','really','and','um',
                            #'kind','of','really',"didn't",'get','together',
                            #'at','all','freshman'])
        #context = ['mom#n','mom#n','were#v','campfire#n','leaders#n',
                            #'together#r','whole#a','bit#n','then#r',
                            #'really#r',
                            #'kind#n','really#r','get#v','together#r','freshman#n']
        #sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='S')
        #self.assertEqual(sum([20,20,103,17,54,13,55,84,11,16,48,16,59,13,16]),sp)
        #sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='A')
        #self.assertEqual(float(sum([20,20,103,17,54,13,55,84,11,16,48,16,59,13,16]))/float(15),sp)

    #def test_foll_semantic_predictability(self):
        #word = WordToken.objects.get(pk = 3863)
        #self.assertEqual([str(x) for x in word.getFollowingContext()], ['he','did','go'])

        #self.assertEqual([str(x) for x in word.getFollowingContext(window=10)],
                        #['he','did','go','to','school','here','and','then',
                        #'um','as','i','said','i','swam','for','ohio','state',
                        #'and','then','i','went','into','agler','davidson','a','sporting',
                        #'goods','store','to','um','buy','a','swimsuit',
                        #'my','sophomore','year'])
        #context = ['did#v','go#v']
        #sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='S')
        #self.assertEqual(sum([51,98]),sp)
        #sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='A')
        #self.assertEqual(float(sum([51,98]))/2.0,sp)

        #context = ['did#v','go#v','school#n','here#r','then#r',
                        #'i#n','said#v','i#n','swam#v','state#n',
                        #'then#r','i#n','went#v','a#n','sporting#a',
                        #'goods#n','store#n','buy#v','a#n','swimsuit#n',
                        #'sophomore#n']
        #sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='S')
        #self.assertEqual(sum([51,98,97,10,11,59,50,59,35,120,11,59,98,66,32,45,91,60,66,12,11]),sp)







