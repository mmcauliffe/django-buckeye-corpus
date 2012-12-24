'''
Created on 2012-07-04

@author: michael
'''
from django.conf.urls.defaults import patterns
from django.conf import settings

urlpatterns = patterns('BuckeyeCorpusBrowser.buckeye.views',
    (r'^$','index'),
    (r'^reset/$','reset'),
    (r'^synsem/(?P<f>\w)/$','synsem'),
    (r'^basic/$','basic'),
    (r'^detail/(?P<tokenNum>\d+)/$','tokenDetails'),
    (r'^outliers/(?P<f>\w+\.\w+)/$','outliers'),
)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}))