from django.conf.urls import patterns, include, url

### Urls
urlpatterns = patterns('',
    url(r'^attachments/(?P<path>.+)$', 'discourse.views.attachments',  name="attachments"),
    url(r'^document/(?P<path>.+)$', 'discourse.views.document',  name="document"),
    url(r'^thread/(?P<path>.+)$', 'discourse.views.thread',  name="thread"),
    url(r'^view/(?P<path>.+)$', 'discourse.views.redirect',  name="discourse"),
)

# Import the events module to ensure signal subscriptions are properly hooked up.
import events
