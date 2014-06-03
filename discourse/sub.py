from datetime import timedelta, datetime

from django.db import models
from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string
from django.dispatch import Signal
from models import Subscription, Notice, Event, get_instance_from_sig, event, model_sig

import logging
logger = logging.getLogger('discourse')


"""

"""

def get_path(obj):
    pass

def get_object_from_path(signature):
    pass


def publish(actor, action, object, **context):
    """
    Log an event performed by actor, of the type, on the object, and any other context arguments needed
    to render notification templates.
    """
    path = get_path(object)

    # Context for templates
    context.update({
        'actor': actor,
        'action': action,
        'object': object,
        'path': path,
        'settings': settings,
    })

    # Gather all users that are subscribed on this path
    subscriptions = Subscription.objects.filter(path=path, toggle=True).select_related('user')
    users = set([s.user for s in subscriptions])

    # We don't notify the actor of her own actions #YesAllWomen
    users.discard( actor )

    # Build the event.
    e = Event(
        actor = actor,
        type = type,
        path = path
    )


def subscribe(user, path):
    pass

def unsubscribe(user, path, forget=False):
    pass

def is_subscribed(user, path):
    pass

def notify(user, event):
    pass

def listen(*paths):
    pass



    # Todo, make sure notifications aren't sent too quickly one after another.

    if isinstance(path, models.Model):
        object = path
        path = model_sig(path)
    else:
        object = get_instance_from_sig(path)

    # Build a context to render templates
    context = context.copy()
    context['actor'] = actor
    context['path'] = path
    context['type'] = type
    context['object'] = object
    context['settings'] = settings
    context['DOMAIN'] = settings.DOMAIN

    # Find users to be notified
    subscriptions = Subscription.objects.filter(path=path, toggle=True)
    users = set([s.user for s in subscriptions])
    users.discard( actor )

    logger.info("Event: %s %s %s", actor, type, path)

    # Create the event, yo
    e = Event(
        actor = actor,
        type = type,
        path = path
    )

    streams = set([actor])

    # Trigger event signal
    # Receivers are expected to alter notify or context.
    for reciever, response in event.send(sender=e, notify=users, streams=streams, **context):
        if isinstance(response, dict):
            context.update(response)

    e.save()

    for stream in streams:
        e.add_to_stream(stream)

    # Notify all the ya'lls
    messages = []
    for user in users:
        notice = Notice.objects.create(user=user)
        notice.events = [e]
        try:
            msg = render_mail(user.email, type, context)
            messages.append(msg)
        except Exception, x:
            print "Error sending email (%s):" % type, x

    # Use default email connection to send the messages.
    if messages:
        connection = mail.get_connection()
        connection.send_messages(messages)

    return e

