import uuid, logging
from datetime import datetime
from django.db import models
from django.dispatch import Signal
from django.conf import settings

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
            'data': simple(data)
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
    def __init__(self, anchor, actor, predicate, target=None, data=None, record=False, when=None):
        self.id = uuid.uuid4().hex
        self.anchor = anchor
        self.actor = actor
        self.predicate = predicate
        self.target = target
        self.data = data or {}
        self.record = record
        self.when = when or datetime.now()
        self.canceled = False

        self.notify = set()         # Users to notify
        self.streams = set()        # Streams to add this event to

    def __unicode__(self):
        return "Event(%r, %r, %r)" % (self.actor, self.predicate, uri(self.anchor))

    def simple(self):
        return {
            'id': self.id,
            'anchor': uri(self.anchor),
            'actor': simple(self.actor),
            'predicate': self.predicate,
            'target': simple(self.target),
            'data': simple(self.data),
            'record': bool(self.record),
            'when': simple(self.when)
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
                anchor_uri = uri(self.anchor),
                actor = self.actor,
                predicate = self.predicate,
                target_uri = uri(self.target),
                data = simple(self.data),
                when = self.when,
            )
            self.record.save()

        self.send_notifications()

        for stream in tuple(self.streams):
            self.record.add_to_stream(stream)

    def send_notifications(self):
        if not self.notify:
            return

        for reciever, result in notification.send(sender=None, event=self, users=self.notify):
            pass
        
        self.notify = set()

    def cancel(self):
        self.canceled = True


def publish(*args, **kwargs):
    return publish_event( Event(*args, **kwargs) )


def publish_event(e):
    e.notify.update( get_followers(e.actor, e.anchor, e.target) )

    for reciever, result in event_signal.send(sender=None, event=e):
        if e.canceled or result is False:
            logger.info("EVENT CANCELED:\n%r", e)
            e.canceled = True
            return False

    e.resolve()

    logger.info("EVENT CREATED:\n%r", e)

    if redis:
        redis.publish(e.anchor_uri, to_json( e.simple() ))

    return e


def on(predicate):
    def decorator(fn):
        hook(predicate, fn)
        return fn
    return decorator


def hook(predicate, fn):
    def subscription(sender, event, **kwargs):
        if predicate == '*' or event.predicate == predicate:
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

    def render(self, context):
        data = self.resolve(context)
        anchor = uri(data.get('anchor'), data.get('sub'))
        request = context['request']
        size = data.get('size', 21)
        comments = data.get('comments', False)
        context_ = data.get('context', None)

        try:
            stream = Stream.objects.get(anchor_uri=anchor)
            events = stream.records.all().order_by('-id')[:size]
            count = stream.events.count()
        except Stream.DoesNotExist:
            stream = Stream(anchor_uri=anchor)
            events = ()
            count = 0

        events = list(events)
        if events:
            last_event_id = events[-1].id
        else:
            last_event_id = None
        
        return render_to_string('discourse/stream.html', {'stream': stream, 
                                                          'events': events,
                                                          'count': count,
                                                          'size': size,
                                                          'context': context_,
                                                          'anchor': anchor, 
                                                          'last_event_id': last_event_id,
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
