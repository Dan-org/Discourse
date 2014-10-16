import uuid
from datetime import datetime
from django.db import models
from django.dispatch import Signal
from django.conf import settings
from uuidfield import UUIDField

try:
    import redis
    redis = redis.Redis(host='localhost', port=6379, db=getattr(settings, 'REDIS_DB', 1))
except ImportError:
    redis = None

from uri import *
from follow import get_followers

notification = Signal(['event', 'users'])
event_signal = Signal(['event'])


class Record(models.Model):
    id = UUIDField(primary_key=True)
    anchor_uri = models.CharField(max_length=255)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="events_generated")
    predicate = models.SlugField()
    target_uri = models.CharField(max_length=255, blank=True)
    when = models.DateTimeField(auto_now_add=True)

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
            'when': simple(self.when)
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
    path = models.CharField(max_length=255)
    records = models.ManyToManyField("discourse.Record", related_name="streams")
    
    class Meta:
        app_label = 'discourse'

    def __unicode__(self):
        return "Stream(%s)" % self.path

    def render_events(self, request, size=10, after=None):
        """
        TODO: Cache this.
        """
        q = self.events.all().order_by('-id')[:size]
        if after:
            q = events.filter(id__gt=after)

        events = []
        for event in q:
            try:
                a = event.object
                events.append(event)
            except models.ObjectDoesNotExist:
                event.delete()

        context = RequestContext(request, {'stream': self})

        for e in events:
            yield e.render(request)

    def get_absolute_url(self):
        obj = get_instance_from_sig(self.path)
        if obj:
            return obj.get_absolute_url()



class Event(object):
    def __init__(self, anchor, actor, predicate, target=None, context=None, record=False, when=None):
        self.id = uuid.uuid4().hex
        self.anchor = anchor
        self.actor = actor
        self.predicate = predicate
        self.target = target
        self.context = context
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
            'context': simple(self.context),
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
            e.canceled = True
            return False

    e.resolve()

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
        if event.predicate == predicate:
            return fn(event)
    event_signal.connect(subscription, weak=False)


def on_notify(fn):
    def subscription(sender, event, users, **kwargs):
        return fn(event, users)
    notification.connect(subscription, weak=False)
