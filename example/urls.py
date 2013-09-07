from django.conf.urls import patterns, include, url

### Views
from views import document, home

### Admin
from django.contrib import admin
admin.autodiscover()

### Urls
urlpatterns = patterns('',
    url(r'^admin/', 	include(admin.site.urls)),
    url(r'^discourse/', include('discourse.urls')),
    
    url(r'^document/$', document, name="home"),

    url(r'^$', home),

)

### Media Serving ###
from django.conf import settings

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )
