# Create your views here.
#from django.core.context_processors import csrf
from django.contrib.auth.decorators import login_required
#from django.contrib.auth import authenticate,login
#from django.contrib.auth.models import User
from django.shortcuts import render,redirect,render_to_response
#from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template import RequestContext



from models import *
from forms import *
from funcs import getSynProbList,addPlural,get_outliers

from StimuliPicker.stimuli.functions import getNouns

from tasks import doBasicAnalysis,doReset


@login_required
def index(request):
    return render(request,'Buckeye/index.html',{})


@login_required
def reset(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = ResetForm(request.POST)
            if form.is_valid() and form.cleaned_data['reset']:
                doReset.delay(request.path.replace("/","_"))
                return redirect(index)
        form = ResetForm()
        return render(request,'Buckeye/forms.html',{'form':form})

@login_required
def basic(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = AnalysisForm(request.POST)
            if form.is_valid():
                doBasicAnalysis.delay(request.path.replace("/","_"),form.cleaned_data)
                return redirect(index)
        form = AnalysisForm()
        return render(request,'Buckeye/forms.html',{'form':form})



#@login_required
#def figureProbs(request):
#    if request.user.is_superuser:
#        if request.method == 'POST':
#            form = ResetForm(request.POST)
#            if form.is_valid() and form.cleaned_data['reset']:
#                doProbStuff.delay(request.path.replace("/","_"))
#                return redirect(index)
#            else:
#                form = ResetForm()
#                render(request,'Buckeye/forms.html',{'form':form})
#        else:
#            form = ResetForm()
#            return render(request,'Buckeye/forms.html',{'form':form})

def addSynSemNouns():
    patterns = set([('DT','NN'),
                    ('NN'),
                    ('DT','SIL','NN'),
                    ('SIL','NN')])
    nouns = set([item for sublist in [addPlural(x) for x in getNouns()] for item in sublist])
    disflu = set(['Other','Disfluency'])
    dets = set(['a','an','the','this','these','those',
                'my','your','their','his','her','our',
                'all','many','some','its','any','few',
                'much','each','every','that'])
    banned_nouns = set(['lot','he','it','is','i','if','as','are','in','few','even',
                        'she','its','when','wow','on','all','two','off','ten','out',
                        'how','well','like','where','but','once','most','one','fifth','only',
                        'of','with','about','that','to','what','me','very','whether','you',
                        'for',"it's",'at',"i'm",'probably','into','and','here','entire',
                        'there','by',"that's",'along','from','other','something','with','while',
                        'little','whatever','can','will','because','our','every',"we're",
                        'them','any','your','think','pretty',"i'll","he's",'make'])
    synlist = getSynProbList()
    words = WordToken.objects.filter(WordType__Label__in = synlist)
    ss = []
    for word in words:
        prev = word.getPreviousWord()
        if prev is None:
            continue
        if prev.Category.CategoryType in disflu:
            continue
        folls = []
        foll = word.getFollowingWord()
        status = 1
        for i in range(3):
            if foll is None:
                break
            if foll.Category.CategoryType in disflu:
                status = 0
                break
            if str(foll) in banned_nouns:
                status = 0
                break
            if str(foll) in dets:
                folls.append('DT')
            elif str(foll) in nouns:
                folls.append('NN')
            elif foll.Category.Label == 'SIL':
                folls.append('SIL')
            foll = foll.getFollowingWord()
        if status == 0:
            continue
        if foll.Category.CategoryType in disflu:
            continue
        if tuple(folls) not in patterns:
            continue
        ss.append(SynSemCase(verb = word,complement=''))
        
    SynSemCase.objects.bulk_create(ss)

def addSynSem():
    patterns = set([('DT','NN'),
                    ('DT','NNS'),
                    ('NN'),
                    ('NNS')])
    disflu = set(['Other','Disfluency','Pause'])
    synlist = getSynProbList()
    cats = set(['NN','NNS'])
    dets = set(['a','an','the'])
    banned_nouns = set(['lot'])
    words = WordToken.objects.filter(WordType__Label__in = synlist)
    ss = []
    for word in words:
        prev = word.getPreviousWord()
        if prev is None:
            continue
        if prev.Category.CategoryType in disflu:
            continue
        foll = word.getFollowingWord()
        folls = []
        status = 1
        for i in range(2):
            if foll is None:
                break
            if foll.Category.Label not in cats and foll.WordType.Label not in dets:
                break
            if foll.Category.CategoryType in disflu:
                status = 0
                break
            if foll.WordType.Label in banned_nouns:
                status = 0
                break
            folls.append(foll)
            foll = foll.getFollowingWord()
        if status == 0:
            continue
        if tuple(x.Category.Label for x in folls) not in patterns:
            continue
        ss.append(SynSemCase(verb = word,complement=''))
        
    SynSemCase.objects.bulk_create(ss)


@login_required
def synsem(request,f):
    if SynSemCase.objects.count() == 0:
        addSynSemNouns()
    qs = SynSemCase.objects.all()
    if f == 'N':
        qs = qs.filter(checked__isnull=True)
    elif f == 'A':
        qs = qs.filter(checked = True)
    elif f == 'E':
        qs = qs.filter(checked = False)
    paginator = Paginator(qs,25)
    page = request.GET.get('page')
    try:
        q = paginator.page(page)
    except PageNotAnInteger:
        q = paginator.page(1)
    except EmptyPage:
        q = paginator.page(paginator.num_pages)
    return render_to_response('Buckeye/list.html',{'cases':q})
        

@login_required
def tokenDetails(request,tokenNum):
    token = WordToken.objects.get(pk=tokenNum)
    if request.method == 'POST':
        form = RedoSpecGramForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['Ceiling'] is not None and form.cleaned_data['NFormants'] is not None:
                token.setSpecVariables(form.cleaned_data['Ceiling'],form.cleaned_data['NFormants'])
                token.setStrFormants()
            elif form.cleaned_data['ManualF1'] is not None and form.cleaned_data['ManualF2'] is not None:
                token.setStrFormants(formants=(form.cleaned_data['ManualF1'],form.cleaned_data['ManualF2']))
            request.method = 'GET'
    token.createPictures()
    form = RedoSpecGramForm()
    return render(request,'Buckeye/detail.html',{'Token':token,'form':form})



@login_required
def outliers(request,f):
    qs = get_outliers(f)
    paginator = Paginator(qs,25)
    page = request.GET.get('page')
    try:
        q = paginator.page(page)
    except PageNotAnInteger:
        q = paginator.page(1)
    except EmptyPage:
        q = paginator.page(paginator.num_pages)
    return render_to_response('Buckeye/outlier_list.html',{'outliers':q})
    
    
    