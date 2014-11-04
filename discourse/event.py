import uuid, logging
from taggit.managers import TaggableManager
from datetime import datetime
from django.db import models
from django.dispatch import Signal
from django.conf import settings

from ajax import to_json
from uuidfield import UUIDField
from yamlfield import YAMLField

try:
    import redis
    redis = redis.Redis(host='localhost', port=6379, db=getattr(settings, 'REDIS_DB', 1))
except ImportError:
    redis = None

from uri import *
from follow import get_followers

logger = logging.getLogger("discourse")



### Signals ###
notification = Signal(['event', 'users'])
event_signal = Signal(['event'])


### Models ###
class Record(models.Model):
    id = UUIDField(primary_key=True)
    anchor_uri = models.CharField(max_length=255)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="events_generated")
    predicate = models.SlugField()
    target_uri = models.CharField(max_length=255, blank=True, null=True)
    when = models.DateTimeField(auto_now_add=True)
    data = YAMLField()

    tags = TaggableManager()

    def __unicode__(self):
        return "Record(%r, %r, %r)" % (self.actor, self.predicate, self.anchor_uri)

    def simple(self):
        return {
            'id': self.id,
            'actor': simple(self.actor),
            'anchor': self.anchor_uri,
            'predicate': self.predicate,
            'target': simple(self.target),
            'record': True,
            'when': simple(self.when),
            'data': simple(data),
            'tags': self.tags
        }

    @property
    def anchor(self):
        if not hasattr(self, '_anchor'):
            self._anchor, self._anchor_extra = resolve_model_uri(self.anchor_uri)
        return self._anchor

    @property
    def target(self):
        if not hasattr(self, '_target'):
            self._target, self._target_extra = resolve_model_uri(self.target_uri)
        return self._target

    @property
    def template(self):
        return "discourse/stream/%s.html" % self.predicate

    class Meta:
        app_label = 'discourse'
        ordering = ['-when']


class Stream(models.Model):
    anchor_uri = models.CharField(max_length=255)
    records = models.ManyToManyField("discourse.Record", related_name="streams")
    
    class Meta:
        app_label = 'discourse'

    def __unicode__(self):
        return "Stream(%s)" % self.anchor_uri

    def render_events(self, request, size=10, after=None):
        """
        TODO: Cache this.
        """
        q = self.records.all().order_by('-id')[:size]
        if after:
            q = q.filter(id__gt=after)

        records = []
        for record in q:
            try:
                a = record.object
                records.append(record)
            except models.ObjectDoesNotExist:
                record.delete()

        context = RequestContext(request, {'stream': self})

        for record in records:
            yield record.render(request)

    def get_absolute_url(self):
        obj = resolve_model_uri(self.anchor_uri)
        if obj:
            return obj.get_absolute_url()


### Support ###
class Event(object):
    def __init__(self, anchor, actor, predicate, target=None, data=None, record=False, when=None, internal=False, tags=None):
        self.id = uuid.uuid4().hex
        if isinstance(anchor, basestring):
            self.anchor, self.sub = resolve_model_uri(anchor)
            if self.anchor is None:
                self.anchor = anchor
        else:
            self.anchor = anchor
            self.sub = None
        self.actor = actor
        self.predicate = predicate
        self.target = target
        self.data = data or {}
        self.record = record
        self.when = when or datetime.now()
        self.internal = internal    # Don't publish to redis.
        self.canceled = False
        self.tags = set(tags or ())

        self.notify = set()         # Users to notify
        self.streams = set()        # Streams to add this event to

    def __unicode__(self):
        return "%s %s at %s" % (self.actor, self.predicate, self.anchor)

    def __repr__(self):
        return "Event(%r, %r, %r)" % (self.actor, self.predicate, uri(self.anchor))

    def simple(self):
        return {
            'id': self.id,
            'anchor': uri(self.anchor, self.sub),
            'actor': simple(self.actor),
            'predicate': self.predicate,
            'target': simple(self.target),
            'data': simple(self.data),
            'record': bool(self.record),
            'when': simple(self.when),
            'tags': simple(self.tags)
        }

    def resolve(self):
        """
        Saves the event, notify members of the .notify set, updates the streams of the .streams set.
        """
        if self.canceled:
            return

        if self.record is True:
            self.record = Record(
                id = self.id,
                anchor_uri = uri(self.anchor, self.sub),
                actor = self.actor,
                predicate = self.predicate,
                target_uri = uri(self.target),
                data = simple(self.data),
                when = self.when,
            )
            self.record.save()
            self.record.tags.add(*self.tags)

        self.send_notifications()

        #for stream in tuple(self.streams):
        #    self.record.add_to_stream(stream)

    def send_notifications(self):
        if not self.notify:
            return

        for reciever, result in notification.send(sender=None, event=self, users=self.notify):
            pass
        
        self.notify = set()

    def cancel(self):
        self.canceled = True

    def publish(self):
        self.notify.update( get_followers(self.actor, self.anchor, self.target) )

        for reciever, result in event_signal.send(sender=None, event=self):
            if self.canceled or result is False:
                logger.info("EVENT CANCELED:\n%r", self)
                self.canceled = True
                return False

        self.resolve()

        logger.debug("%s\n%s" % (self, self.simple()))

        if redis and not self.internal:
            redis.publish(uri(self.anchor), to_json( self.simple() ))

        return self



def publish(*args, **kwargs):
    return Event(*args, **kwargs).publish()


def on(*predicates):
    def decorator(fn):
        hook(fn, *predicates)
        return fn
    return decorator


def hook(fn, *predicates):
    def subscription(sender, event, **kwargs):
        if '*' in predicates or event.predicate in predicates:
            return fn(event)
    event_signal.connect(subscription, weak=False)


def on_notify(fn):
    def subscription(sender, event, users, **kwargs):
        return fn(event, users)
    notification.connect(subscription, weak=False)


### Template Tagds ###
import ttag
from django.template.loader import render_to_string


class StreamTag(ttag.Tag):
    """
    Show a stream for an object
    {% stream object %}

    Show a stream for a string
    {% stream 'pandas' %}

    Set the initial size of shown events to 5 instead of the default of 21:
    {% stream object size=5 %}

    Allow comments
    {% stream object comments=True %}

    Set the context
    {% stream object context="home-page" %}
    """
    anchor = ttag.Arg(required=True)
    size = ttag.Arg(required=False, keyword=True)
    comments = ttag.Arg(required=False, keyword=True)
    context_ = ttag.Arg(required=False, keyword=True)
    tags = ttag.Arg(required=False, keyword=True)

    def render(self, context):
        data = self.resolve(context)
        anchor = uri(data.get('anchor'), data.get('sub'))
        request = context['request']
        size = data.get('size', 21)
        comments = data.get('comments', False)
        context_ = data.get('context', None)
        tags = set(data.get('tags', '').lower().split())

        try:
            records = Record.objects.filter(anchor_uri=anchor)
            if tags:
                records = records.filter(tags__name__in=tags)
            count = records.count()
            records = records.order_by('-id')[:size]
        except Stream.DoesNotExist:
            records = ()
            count = 0

        records = list(records)
        if records:
            last_id = records[-1].id
        else:
            last_id = None
        
        return render_to_string('discourse/stream.html', {'records': records,
                                                          'count': count,
                                                          'size': size,
                                                          'context': context_,
                                                          'anchor_uri': anchor,
                                                          'last_id': last_id,
                                                          'auth_login': settings.LOGIN_REDIRECT_URL}, context)

    class Meta:
        name = "stream"


### Views ###
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def monitor(request):
    """
    Monitor all events happening on the system.
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    events = Record.objects.all()[:50]
    return render(request, 'discourse/monitor.html', locals())


def stream(request, path):
    """

    """
    stream = get_object_or_404(Stream, path=path.rstrip('/'))
    last = request.GET.get('last', None)
    if last:
        events = stream.events.filter(id__lt=last)
    else:
        events = stream.events.all()

    results = []
    last_event_id = None
    for e in events[:21]:
        last_event_id = e.id
        results.append( e.render(request) )

    if events.count() >= 21:
        next = '%s?%s' % (request.path, last_event_id)
    else:
        next = None

    return HttpResponse(json.dumps( {
        'count': events.count(),
        'size': len(results),
        'results': results,
        'next': next,
    } ), content_type="application/json")
