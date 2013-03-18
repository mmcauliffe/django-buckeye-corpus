# Create your views here.
#from django.core.context_processors import csrf
from django.contrib.auth.decorators import login_required
#from django.contrib.auth import authenticate,login
#from django.contrib.auth.models import User
from django.shortcuts import render,redirect,render_to_response
#from django.http import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template import RequestContext
from django.conf import settings



from .models import *
from .forms import *
from .utils import get_outliers
from .tasks import doBasicAnalysis,doReset

def testAnalysis(form):
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
    vows = ['aa','ae','eh','ey','ih','iy','ow','uh','uw']
    words = WordToken.objects.all()
    words = words.filter(WordType__CVSkel='CVC')
    words = words.filter(WordType__Label__in = goodWords).order_by('Dialog')
    words = words.filter(Dialog__Speaker__Number = 's03')
    allout = []
    for w in words:
        if not w.isAcceptable():
            continue
        allout.extend(w.getAnalysisLines(form))
    if not os.isdir(fetch_media_resource("Results/Buckeye")):
        os.mkdir(fetch_media_resource("Results/Buckeye"))
    with open(fetch_media_resource("Results/Buckeye/analysis.txt"),'w') as f:
        f.write("\t".join(allout[0][0].keys()))
        f.write("\n")
        for l in allout:
            for line in l:
                f.write("\t".join(map(str,line.values())))
                f.write("\n")


@login_required
def index(request):
    return render(request,'buckeyebrowser/index.html',{})


@login_required
def reset(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = ResetForm(request.POST)
            if form.is_valid() and form.cleaned_data['reset']:
                doReset.delay(request.path.replace("/","_"))
                return redirect(index)
        form = ResetForm()
        return render(request,'buckeyebrowser/form.html',{'form':form})

@login_required
def basic(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = AnalysisForm(request.POST)
            if form.is_valid():
                doBasicAnalysis.delay(form)
                return redirect(index)
        form = AnalysisForm()
        return render(request,'buckeyebrowser/form.html',{'form':form})


#def addSynSemNouns():
    #patterns = set([('DT','NN'),
                    #('NN'),
                    #('DT','SIL','NN'),
                    #('SIL','NN')])
    #nouns = set([item for sublist in [addPlural(x) for x in getNouns()] for item in sublist])
    #disflu = set(['Other','Disfluency'])
    #dets = set(['a','an','the','this','these','those',
                #'my','your','their','his','her','our',
                #'all','many','some','its','any','few',
                #'much','each','every','that'])
    #banned_nouns = set(['lot','he','it','is','i','if','as','are','in','few','even',
                        #'she','its','when','wow','on','all','two','off','ten','out',
                        #'how','well','like','where','but','once','most','one','fifth','only',
                        #'of','with','about','that','to','what','me','very','whether','you',
                        #'for',"it's",'at',"i'm",'probably','into','and','here','entire',
                        #'there','by',"that's",'along','from','other','something','with','while',
                        #'little','whatever','can','will','because','our','every',"we're",
                        #'them','any','your','think','pretty',"i'll","he's",'make'])
    #synlist = getSynProbList()
    #words = WordToken.objects.filter(WordType__Label__in = synlist)
    #ss = []
    #for word in words:
        #prev = word.getPreviousWord()
        #if prev is None:
            #continue
        #if prev.Category.CategoryType in disflu:
            #continue
        #folls = []
        #foll = word.getFollowingWord()
        #status = 1
        #for i in range(3):
            #if foll is None:
                #break
            #if foll.Category.CategoryType in disflu:
                #status = 0
                #break
            #if str(foll) in banned_nouns:
                #status = 0
                #break
            #if str(foll) in dets:
                #folls.append('DT')
            #elif str(foll) in nouns:
                #folls.append('NN')
            #elif foll.Category.Label == 'SIL':
                #folls.append('SIL')
            #foll = foll.getFollowingWord()
        #if status == 0:
            #continue
        #if foll.Category.CategoryType in disflu:
            #continue
        #if tuple(folls) not in patterns:
            #continue
        #ss.append(SynSemCase(verb = word,complement=''))

    #SynSemCase.objects.bulk_create(ss)

#def addSynSem():
    #patterns = set([('DT','NN'),
                    #('DT','NNS'),
                    #('NN'),
                    #('NNS')])
    #disflu = set(['Other','Disfluency','Pause'])
    #synlist = getSynProbList()
    #cats = set(['NN','NNS'])
    #dets = set(['a','an','the'])
    #banned_nouns = set(['lot'])
    #words = WordToken.objects.filter(WordType__Label__in = synlist)
    #ss = []
    #for word in words:
        #prev = word.getPreviousWord()
        #if prev is None:
            #continue
        #if prev.Category.CategoryType in disflu:
            #continue
        #foll = word.getFollowingWord()
        #folls = []
        #status = 1
        #for i in range(2):
            #if foll is None:
                #break
            #if foll.Category.Label not in cats and foll.WordType.Label not in dets:
                #break
            #if foll.Category.CategoryType in disflu:
                #status = 0
                #break
            #if foll.WordType.Label in banned_nouns:
                #status = 0
                #break
            #folls.append(foll)
            #foll = foll.getFollowingWord()
        #if status == 0:
            #continue
        #if tuple(x.Category.Label for x in folls) not in patterns:
            #continue
        #ss.append(SynSemCase(verb = word,complement=''))

    #SynSemCase.objects.bulk_create(ss)


#@login_required
#def synsem(request,f):
    #if SynSemCase.objects.count() == 0:
        #addSynSemNouns()
    #qs = SynSemCase.objects.all()
    #if f == 'N':
        #qs = qs.filter(checked__isnull=True)
    #elif f == 'A':
        #qs = qs.filter(checked = True)
    #elif f == 'E':
        #qs = qs.filter(checked = False)
    #paginator = Paginator(qs,25)
    #page = request.GET.get('page')
    #try:
        #q = paginator.page(page)
    #except PageNotAnInteger:
        #q = paginator.page(1)
    #except EmptyPage:
        #q = paginator.page(paginator.num_pages)
    #return render_to_response('Buckeye/list.html',{'cases':q})


@login_required
def token_details(request,tokenNum):
    token = WordToken.objects.select_related('Dialog','WordType','Dialog__Speaker').get(pk=tokenNum)
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
    output = token.get_details()
    return render(request,'buckeyebrowser/detail.html',{'output':output,'form':form})



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
    return render_to_response('buckeyebrowser/outlier_list.html',{'outliers':q})


