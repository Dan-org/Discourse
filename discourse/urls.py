from django.conf.urls import patterns, include, url

### Urls
urlpatterns = patterns('discourse',
    url(r'^thread/(?P<uri>.+)$', 'thread.manipulate',  name="thread"),
    url(r'^library/(?P<uri>.+)$', 'library.manipulate',  name="library"),
    url(r'^document/(?P<uri>.+)$', 'document.manipulate',  name="document"),
    url(r'^follow/$', 'follow.manipulate', name="follow"),
    url(r'^favorite/$', 'favorite.manipulate', name="favorite"),
    url(r'^monitor/$', 'event.monitor',  name="monitor"),
    url(r'^stream/(?P<uri>.+)$', 'event.stream',  name="stream"),
    url(r'^vote/(?P<uri>.+)$', 'vote.cast',  name="vote"),
)
