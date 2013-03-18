"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


from linghelper import DTW,getSemanticRelatedness

from .models import *


class BuckeyeTest(TestCase):
    fixtures = ['buckeyebrowser_testdata.json']
    def test_prev_semantic_predictability(self):
        word = WordToken.objects.get(pk = 3863)
        self.assertEqual([str(x) for x in word.getPreviousContext()], ['kind','of','really',
                                                    "didn't",'get','together',
                                                    'at','all','freshman'])
        context = ['kind#n','really#r','get#v','together#r','freshman#n']
        sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='S')
        self.assertEqual(sum([48,16,59,13,16]),sp)
        sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='A')
        self.assertEqual(float(sum([48,16,59,13,16]))/float(5),sp)

        self.assertEqual([str(x) for x in word.getPreviousContext(window=10)],
                            ['mom','an','his','mom','were','campfire','leaders',
                            'together','and','the','whole','bit','and','then',
                            'we','didn\'t','really','and','um',
                            'kind','of','really',"didn't",'get','together',
                            'at','all','freshman'])
        context = ['mom#n','mom#n','were#v','campfire#n','leaders#n',
                            'together#r','whole#a','bit#n','then#r',
                            'really#r',
                            'kind#n','really#r','get#v','together#r','freshman#n']
        sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='S')
        self.assertEqual(sum([20,20,103,17,54,13,55,84,11,16,48,16,59,13,16]),sp)
        sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='A')
        self.assertEqual(float(sum([20,20,103,17,54,13,55,84,11,16,48,16,59,13,16]))/float(15),sp)

    def test_foll_semantic_predictability(self):
        word = WordToken.objects.get(pk = 3863)
        self.assertEqual([str(x) for x in word.getFollowingContext()], ['he','did','go'])

        self.assertEqual([str(x) for x in word.getFollowingContext(window=10)],
                        ['he','did','go','to','school','here','and','then',
                        'um','as','i','said','i','swam','for','ohio','state',
                        'and','then','i','went','into','agler','davidson','a','sporting',
                        'goods','store','to','um','buy','a','swimsuit',
                        'my','sophomore','year'])
        context = ['did#v','go#v']
        sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='S')
        self.assertEqual(sum([51,98]),sp)
        sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='A')
        self.assertEqual(float(sum([51,98]))/2.0,sp)

        context = ['did#v','go#v','school#n','here#r','then#r',
                        'i#n','said#v','i#n','swam#v','state#n',
                        'then#r','i#n','went#v','a#n','sporting#a',
                        'goods#n','store#n','buy#v','a#n','swimsuit#n',
                        'sophomore#n']
        sp = getSemanticRelatedness('#'.join([word.WordType.Label,'n']),context,style='S')
        self.assertEqual(sum([51,98,97,10,11,59,50,59,35,120,11,59,98,66,32,45,91,60,66,12,11]),sp)







