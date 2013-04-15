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
from .tasks import do_analysis,do_reset

@login_required
def index(request):
    return render(request,'buckeyebrowser/index.html',{})


@login_required
def reset(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = ResetForm(request.POST)
            if form.is_valid() and form.cleaned_data['reset']:
                do_reset.delay(request.path.replace("/","_"))
                return redirect(index)
        form = ResetForm()
        return render(request,'buckeyebrowser/form.html',{'form':form})

@login_required
def reset_cache(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = ResetCacheForm(request.POST)
            if form.is_valid():
                fields_to_reset = form.cleaned_data['fields_to_reset'].split(',')
                wt = WordToken.objects.filter(Output__isnull=False)
                for w in wt:
                    w.Output = {x:w.Output[x] for x in w.Output if x not in fields_to_reset}
                    w.save()
                return redirect(index)
        form = ResetCacheForm()
        return render(request,'buckeyebrowser/form.html',{'form':form})


@login_required
def basic(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = AnalysisForm(request.POST)
            if form.is_valid():
                do_analysis.delay(form)
                return redirect(index)
        form = AnalysisForm()
        return render(request,'buckeyebrowser/form.html',{'form':form})


@login_required
def token_details(request,tokenNum):
    token = WordToken.objects.select_related('Dialog','WordType','Dialog__Speaker').get(pk=tokenNum)
    if request.method == 'POST':
        form = RedoSpecGramForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['Ceiling'] is not None and form.cleaned_data['NFormants'] is not None:
                token.set_spec_variables(form.cleaned_data['Ceiling'],form.cleaned_data['NFormants'])
                token.set_stress_formants()
            elif form.cleaned_data['ManualF1'] is not None and form.cleaned_data['ManualF2'] is not None:
                token.set_stress_formants(formants=(form.cleaned_data['ManualF1'],form.cleaned_data['ManualF2']))
            request.method = 'GET'
    token.create_pictures()
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


