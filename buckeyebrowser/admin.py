'''
Created on 2012-07-08

@author: michael
'''
from .models import *
from .forms import *
from django.contrib import admin
from django.utils.translation import ugettext, ugettext_lazy as _


class DropDownFilter(admin.RelatedFieldListFilter):
    template = "admin/select_filter.html"


class SpeakerAdmin(admin.ModelAdmin):
    model = Speaker
    list_display = ('Number','Gender','Age','NumFormants','Ceiling')

admin.site.register(Speaker, SpeakerAdmin)

class DialogAdmin(admin.ModelAdmin):
    model = Dialog
    list_display = ('Speaker','Number')

admin.site.register(Dialog, DialogAdmin)

class CategoryAdmin(admin.ModelAdmin):
    model = Category
    list_display = ('Label','CategoryType','Description')

admin.site.register(Category, CategoryAdmin)

class SegmentInline(admin.TabularInline):
    model = SegmentToken

class WordTokenAdmin(admin.ModelAdmin):
    model = WordToken
    inlines = [SegmentInline]
    list_display = ('WordType','Begin','End','Category','Dialog','DialogPart','getFollowingWord')
    list_filter = (('Category',DropDownFilter)
                   ,('Dialog',DropDownFilter))
    search_fields = ['WordType__Label']
admin.site.register(WordToken, WordTokenAdmin)

class SegmentTypeAdmin(admin.ModelAdmin):
    model = SegmentType
    list_display = ('Label','Syllabic','Obstruent','Nasal','Vowel')

admin.site.register(SegmentType, SegmentTypeAdmin)

class WordTypeAdmin(admin.ModelAdmin):
    model = WordType
    list_display = ('Label','getUR')

admin.site.register(WordType, WordTypeAdmin)

#class SynSemCaseAdmin(admin.ModelAdmin):
    #model = SynSemCase
    #list_display = ('verb','checked')
    #list_filter = ('checked',)
    #formfield_overrides = {
        #models.ForeignKey: {'widget': forms.HiddenInput() }
    #}

#admin.site.register(SynSemCase, SynSemCaseAdmin)
