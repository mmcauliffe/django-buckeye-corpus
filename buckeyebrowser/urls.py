'''
Created on 2012-07-04

@author: michael
'''
from django.conf.urls import patterns

urlpatterns = patterns('buckeyebrowser.views',
    (r'^$','index'),
    (r'^reset/$','reset'),
    #(r'^synsem/(?P<f>\w)/$','synsem'),
    (r'^basic/$','basic'),
    (r'^resetcache/$','reset_cache'),
    (r'^detail/(?P<tokenNum>\d+)/$','token_details'),
    (r'^outliers/(?P<f>\w+\.\w+)/$','outliers'),

)

