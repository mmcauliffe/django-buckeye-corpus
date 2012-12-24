'''
Created on 2012-07-04

@author: michael
'''
from django import forms

class ResetForm(forms.Form):
    reset = forms.BooleanField(initial=True)
    
    
class SynSemForm(forms.Form):
    CHOICES = (('N','Unclassified'),
               ('A','Accepted'),
               ('E','Excluded'))
    Filter = forms.CharField(label='Filter cases by')
    Filter.widget = forms.Select(choices=CHOICES)
    
class RedoSpecGramForm(forms.Form):
    Ceiling= forms.IntegerField(required=False)
    NFormants = forms.FloatField(required=False,label='Number of formants')
    ManualF1 = forms.FloatField(required=False,label='Manual F1')
    ManualF2 = forms.FloatField(required=False,label='Manual F2')
    
class AnalysisForm(forms.Form):
    mChoices = (('S','SSANOVA-style'),
                ('M','Midpoint'),
                ('D','Dispersion'))
    sourceChoices = (('N','None'),
                     ('B','Buckeye'),
                  ('C','CELEX'),
                  ('I','IPHOD'))
    phonoProbChoices = (('N','None'),
                        ('B','BLICK - Hayes'),
                        ('V','Vitevitch & Luce'))
    measure = forms.CharField(label='Measure')
    DispersionFromAH = forms.BooleanField(initial=False,required=False,label="Dispersion from a speaker's AH tokens")
    measure.widget = forms.Select(choices=mChoices)
    placeInDialog = forms.BooleanField(initial=True,required=False,label='Time since beginning of dialog')
    speakingRates = forms.BooleanField(initial=True,required=False,label='Speaking rates')
    contextProbs = forms.BooleanField(initial=True,required=False,label='Contextual probabilities')
    repetitions = forms.BooleanField(initial=True,required=False,label='Repetitions')
    wasRepeated = forms.BooleanField(initial=False,required=False,label='Was repeated')
    wordDuration = forms.BooleanField(initial=True,required=False,label='Word duration')
    segmentalDurations = forms.BooleanField(initial=True,required=False,label='Segmental duration')
    category = forms.CharField(label='Category source')
    category.widget = forms.Select(choices=sourceChoices)
    frequency = forms.CharField(label='Frequency source')
    frequency.widget = forms.Select(choices=sourceChoices)
    nd = forms.CharField(label='Neighbourhood density source')
    nd.widget = forms.Select(choices=sourceChoices)
    phonotactic = forms.CharField(label='Phonotactic probability source')
    phonotactic.widget = forms.Select(choices=phonoProbChoices)
    gender = forms.BooleanField(initial=True,required=False,label='Gender')
    age = forms.BooleanField(initial=True,required=False,label='Age')
    globalSpeakingRate = forms.BooleanField(initial=True,required=False,label='Global speaking rate')
    orthoLength = forms.BooleanField(initial=True,required=False,label='Orthographic length')
    phonoLength = forms.BooleanField(initial=True,required=False,label='Phonological length')
    numSylls = forms.BooleanField(initial=True,required=False,label='Number of syllables')
    semPred = forms.BooleanField(initial=True,required=False,label='Semantic predictability')
    
    class Meta:
        fieldsets = ((None,
                      {'fields':('measure',
                                 'DispersionFromAH')}),
                     ('Lexical type factors',
                      {'fields':('frequency',
                                 'category',
                                 'nd',
                                 'phonotactic',
                                 'orthoLength',
                                 'phonoLength',
                                 'numSylls')}),
                     ('Lexical token factors',
                      {'fields':('wordDuration',
                                 'segmentalDurations')}),
                     ('Contextual factors',
                      {'fields':('speakingRates',
                                 'contextProbs',
                                 'repetitions',
                                 'wasRepeated',
                                 'semPred')}),
                     ('Speaker factors',
                      {'fields':('gender',
                                 'age',
                                 'globalSpeakingRate')}))
        
        