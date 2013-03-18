'''
Created on 2012-07-04

@author: michael
'''
from django import forms
from django.conf import settings

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
    M_CHOICES = (('N','None'),
                ('S','SSANOVA-style'),
                ('M','Midpoint'),
                ('D','Dispersion'))
    if 'celex' in settings.INSTALLED_APPS:
        FREQ_CHOICES = (('N','None'),
                     ('B','Buckeye'),
                  ('C','CELEX'),
                  ('S','SUBTLEX'))
        CAT_CHOICES = (('N','None'),
                     ('B','Buckeye'),
                  ('C','CELEX'))
    else:
        FREQ_CHOICES = (('N','None'),
                     ('B','Buckeye'))
        CAT_CHOICES = (('N','None'),
                     ('B','Buckeye'))
    if 'phonostats' in settings.INSTALLED_APPS:
        PHONO_PROB_CHOICES = (('N','None'),
                        ('VB','Vitevitch & Luce from Buckeye corpus words'),
                        ('VP','Vitevitch & Luce from PhonoStats module'),
                        ('B','BLICK metric from PhonoStats module'))
    else:
        PHONO_PROB_CHOICES = (('N','None'),
                            ('VB','Vitevitch & Luce from Buckeye corpus words'))
    if 'phonostats' in settings.INSTALLED_APPS:
        NEIGH_DEN_CHOICES = (('N','None'),
                        ('B','Neighbourhood based on Buckeye words'),
                        ('PS','Neighbourhood based on PhonoStats module'),
                        ('C','Neighbourhood based on CELEX'))
    else:
        NEIGH_DEN_CHOICES = (('N','None'),
                            ('B','Neighbourhood based on Buckeye words'))
    SEM_PRED_WINDOW = tuple([('A','Auto')]+ [('%d' % x, '%d second' % x) for x in range(1,11)])
    SEM_PRED_STYLE = (('A','Average'),
                        ('S','Sum'),
                        ('W','Weighted'))
    LEX_SCALE_CHOICES = (('C','CELEX'),
                            ('W','Whole corpus'),
                            ('S','Speaker'),
                            ('G','Same gender'),
                            ('A','Same age'),
                            ('D','Dialog'),)
    #FETCH_CHOICES = (('PrevSemPred','PrevSemPred'),
    #                'FollSemPred','FollSemPred')
    measure = forms.CharField(label='Measure')
    measure.widget = forms.Select(choices=M_CHOICES)
    DispersionFromAH = forms.BooleanField(initial=False,required=False,label="Dispersion from a speaker's AH tokens")
    placeInDialog = forms.BooleanField(initial=True,required=False,label='Time since beginning of dialog')
    speakingRates = forms.BooleanField(initial=True,required=False,label='Speaking rates')
    contextProbs = forms.BooleanField(initial=True,required=False,label='Contextual probabilities')
    repetitions = forms.BooleanField(initial=True,required=False,label='Repetitions')
    wasRepeated = forms.BooleanField(initial=False,required=False,label='Was repeated')
    wordDuration = forms.BooleanField(initial=True,required=False,label='Word duration')
    segmentalDurations = forms.BooleanField(initial=True,required=False,label='Segmental duration')
    category = forms.CharField(required=False,label='Category source')
    category.widget = forms.CheckboxSelectMultiple(choices=CAT_CHOICES)
    frequency = forms.BooleanField(initial=True,required=False,label='Frequency')
    nd = forms.BooleanField(initial=True,required=False,label='Neighbourhood density')
    phonotactic = forms.BooleanField(initial=True,required=False,label='Phonotactic probability')
    lexical_scale = forms.CharField(required=False,label = 'Corpora to use for lexical statistics')
    lexical_scale.widget = forms.CheckboxSelectMultiple(choices=LEX_SCALE_CHOICES)
    additional_phono_stats = forms.BooleanField(initial=False,required=False,label='Additional phonological statistics')
    gender = forms.BooleanField(initial=True,required=False,label='Gender')
    age = forms.BooleanField(initial=True,required=False,label='Age')
    globalSpeakingRate = forms.BooleanField(initial=True,required=False,label='Global speaking rate')
    orthoLength = forms.BooleanField(initial=True,required=False,label='Orthographic length')
    phonoLength = forms.BooleanField(initial=True,required=False,label='Phonological length')
    numSylls = forms.BooleanField(initial=True,required=False,label='Number of syllables')
    prev_sem_pred = forms.BooleanField(initial=True,required=False,label='Previous semantic predictability')
    foll_sem_pred = forms.BooleanField(initial=True,required=False,label='Following semantic predictability')
    pause_dist = forms.BooleanField(initial=True,required=False,label='Distance to pauses')
    sem_pred_window = forms.CharField(required=False,label='Semantic predictability window')
    sem_pred_window.widget = forms.CheckboxSelectMultiple(choices=SEM_PRED_WINDOW)
    sem_pred_style = forms.CharField(required=False,label='Semantic predictability style')
    sem_pred_style.widget = forms.CheckboxSelectMultiple(choices=SEM_PRED_STYLE)

    #force_fetch = forms.CharField(label='Force fetch')
    #force_fetch.widget = forms.CheckboxSelectMultiple(choices=FETCH_CHOICES)

    def get_wanted_fields(self):
        form = self.cleaned_data
        wanted_fields =['Word','Token','Vowel','PrevCons','FollCons','Speaker']
        if form['segmentalDurations']:
            wanted_fields.extend(['VowDur','OtherDur'])
        if form['speakingRates']:
            wanted_fields.extend(['PrevSpeakRate','FollSpeakRate','AvgSpeakRate'])
        if form['contextProbs']:
            wanted_fields.extend(['PrevCondProb','FollCondProb'])
        if form['repetitions']:
            wanted_fields.extend(['Repetitions'])
        if form['wasRepeated']:
            wanted_fields.extend(['wasRepeated','wasRepeatedRecently'])
        if 'B' in form['category']:
            wanted_fields.extend(['BuckeyeCategory'])
        if 'C' in form['category']:
            wanted_fields.extend(['CelexCategory'])

        if form['wordDuration']:
            wanted_fields.extend(['WordDuration','BaselineDur'])

        if form['frequency']:
            if 'C' in form['lexical_scale']:
                wanted_fields.extend(['CelexFrequency'])
            if 'W' in form['lexical_scale']:
                wanted_fields.extend(['BuckeyeFrequency'])
            if 'S' in form['lexical_scale']:
                wanted_fields.extend(['SpeakerFrequency'])
            if 'A' in form['lexical_scale']:
                wanted_fields.extend(['AgeFrequency'])
            if 'G' in form['lexical_scale']:
                wanted_fields.extend(['GenderFrequency'])
            if 'D' in form['lexical_scale']:
                wanted_fields.extend(['DialogFrequency'])

        if form['gender']:
            wanted_fields.extend(['SpeakerGender'])
        if form['age']:
            wanted_fields.extend(['SpeakerAge'])

        if form['orthoLength']:
            wanted_fields.extend(['OrthoLength'])
        if form['phonoLength']:
            wanted_fields.extend(['PhonoLength'])
        if form['nd']:
            if 'C' in form['lexical_scale']:
                wanted_fields.extend(['CelexNeighDen','CelexFWND'])
            if 'W' in form['lexical_scale']:
                wanted_fields.extend(['BuckeyeNeighDen','BuckeyeFWND'])
            if 'S' in form['lexical_scale']:
                wanted_fields.extend(['SpeakerNeighDen','SpeakerFWND'])
            if 'A' in form['lexical_scale']:
                wanted_fields.extend(['AgeNeighDen','AgeFWND'])
            if 'G' in form['lexical_scale']:
                wanted_fields.extend(['GenderNeighDen','GenderFWND'])
            if 'D' in form['lexical_scale']:
                wanted_fields.extend(['DialogNeighDen','DialogFWND'])

        if form['additional_phono_stats']:
            wanted_fields.extend(['PhonoStatsNeighDen'])
            wanted_fields.extend(['PhonoStatsBlickPhono'])
            wanted_fields.extend(['PhonoStatsSPhoneProb','PhonoStatsBiPhoneProb'])

        if form['phonotactic']:
            if 'C' in form['lexical_scale']:
                wanted_fields.extend(['CelexSPhoneProb','CelexBiPhoneProb'])
            if 'W' in form['lexical_scale']:
                wanted_fields.extend(['BuckeyeSPhoneProb','BuckeyeBiPhoneProb'])
            if 'S' in form['lexical_scale']:
                wanted_fields.extend(['SpeakerSPhoneProb','SpeakerBiPhoneProb'])
            if 'A' in form['lexical_scale']:
                wanted_fields.extend(['AgeSPhoneProb','AgeBiPhoneProb'])
            if 'G' in form['lexical_scale']:
                wanted_fields.extend(['GenderSPhoneProb','GenderBiPhoneProb'])
            if 'D' in form['lexical_scale']:
                wanted_fields.extend(['DialogSPhoneProb','DialogBiPhoneProb'])

        for w in eval(form['sem_pred_window']):
            for s in eval(form['sem_pred_style']):
                if form['prev_sem_pred']:
                    wanted_fields.extend(['%sWindowPrev%sSemPred' %(w,s)])
                if form['foll_sem_pred']:
                    wanted_fields.extend(['%sWindowFoll%sSemPred' %(w,s)])
        if form['pause_dist']:
            wanted_fields.extend(['DistFollPause','DistPrevPause'])
        if form['placeInDialog']:
            wanted_fields.extend(['placeInDialog'])
        if form['measure'] == 'D':
            if form['DispersionFromAH']:
                wanted_fields += ['AHDispersion']
            else:
                wanted_fields += ['Dispersion']
        if form['measure'] != 'N':
            wanted_fields += ['F1','F2']
        return wanted_fields

    class Meta:
        fieldsets = ((None,
                      {'fields':('measure')}),
                     ('Lexical type factors',
                      {'fields':('lexical_scale',
                                'frequency',
                                 'category',
                                 'nd',
                                 'phonotactic',
                                 'orthoLength',
                                 'phonoLength',
                                 'numSylls',
                                 'additional_phono_stats')}),
                     ('Lexical token factors',
                      {'fields':('wordDuration',
                                 'segmentalDurations')}),
                     ('Contextual factors',
                      {'fields':('speakingRates',
                                 'contextProbs',
                                 'repetitions',
                                 'wasRepeated',
                                 'prev_sem_pred',
                                 'foll_sem_pred',
                                 'pause_dist')}),
                     ('Speaker factors',
                      {'fields':('gender',
                                 'age',
                                 'globalSpeakingRate')}))

