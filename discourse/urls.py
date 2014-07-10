from django.conf.urls import patterns, include, url

### Urls
urlpatterns = patterns('',
    url(r'^attachments/(?P<path>.+)$', 'discourse.views.attachments',  name="attachments"),
    url(r'^zip/(?P<hash>.+)$', 'discourse.views.zip', name="zip"),
    url(r'^document/(?P<path>.+)$', 'discourse.views.document',  name="document"),
    url(r'^thread/(?P<path>.+)$', 'discourse.views.thread',  name="thread"),
    url(r'^vote/$', 'discourse.views.vote', name="vote"),
    url(r'^subscribe/$', 'discourse.views.subscriber', name="subscribe"),
    url(r'^view/(?P<path>.+)$', 'discourse.views.redirect',  name="discourse"),
    url(r'^property/(?P<path>.+)$', 'discourse.views.property',  name="property"),

    url(r'^monitor/$', 'discourse.views.monitor',  name="monitor"),

    url(r'^test/$', 'discourse.views.test',  name="test"),
)

# Import the events module to ensure signal subscriptions are properly hooked up.
import events
