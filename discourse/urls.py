from django.conf.urls import patterns, include, url

### Urls
urlpatterns = patterns('discourse',
    #url(r'^thread/(?P<uri>.+)$', 'thread.manipulate',  name="thread"),
    url(r'^library/(?P<channel>.+?/.+?/.+?)/(?P<filename>.*?)/?$', 'library.manipulate',  name="library"),

    url(r'^document/(?P<uri>.+)$', 'document.manipulate', name="document"),
    url(r'^follow/$', 'follow.manipulate', name="follow"),
    url(r'^favorite/$', 'favorite.manipulate', name="favorite"),

    url(r'^library/get-filename/$', 'library.filename_for_url', name="filename_for_url"),

    #url(r'^monitor/$', 'event.monitor',  name="monitor"),
    #url(r'^stream/(?P<uri>.+)$', 'event.stream',  name="stream"),
    #url(r'^vote/(?P<uri>.+)$', 'vote.cast',  name="vote"),

    url(r'^(?P<channel>.+?)/attachments/(?P<attachment>\w+)/(?P<filename>.+?)$', 'message.attachment',  name="attachment"),
    url(r'^(?P<id>.+)/~regenerate/$', 'message.channel_regenerate', name="channel_regenerate"),
    url(r'^(?P<id>.+)/$', 'message.channel_view', name="channel"),

)
