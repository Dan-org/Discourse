from datetime import timedelta, datetime

from django.db import models
from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string
from django.dispatch import Signal
from models import Subscription, Notice, Event, get_instance_from_sig, event, model_sig

import logging
logger = logging.getLogger('discourse')


### Helpers ###
def render_mail(to, slug, context, from_address=None, template_path='mail/', bcc=None, headers=None):
    """
    Renders an EmailMultiAlternatives object to be sent to the given address, based on the slug.

    For example, given a slug "invite", three templates will be rendered:
        
        discourse/mail/invite.subject.txt     creates the subject line
        discourse/mail/invite.txt             creates the plain text version
        discourse/mail/invite.html            creates the html version

    """
    if isinstance(to, basestring):
        to = [to]
    if from_address is None:
        from_address = settings.DEFAULT_FROM_EMAIL
    subject = render_to_string("%s%s.subject.txt" % (template_path, slug), context).strip()
    html = render_to_string("%s%s.html" % (template_path, slug), context)
    text = render_to_string("%s%s.txt" % (template_path, slug), context)
    msg = mail.EmailMultiAlternatives(subject, text, from_address, to=to, bcc=bcc, headers=headers)
    msg.attach_alternative(html, "text/html")
    return msg


def send_mail(to, slug, context=None, from_address=None, template_path='discourse/mail/', bcc=None, headers=None):
    """
    Convenience function to render and send an email message.  See ``render_mail()`` above for more
    information.
    """
    context = context or {}
    context['settings'] = settings
    msg = render_mail(to, slug, context, from_address, bcc=bcc, headers=headers)
    msg.send()


def subscribe(user, path, force=False):
    """
    Subscribe a user to a path, thereon whenever an update occurs on the path, the user will be
    notified of the event.
    """
    if isinstance(path, models.Model):
        path = model_sig(path)
    sub, _ = Subscription.objects.get_or_create(user=user, path=path)
    if force:
        sub.toggle = True
        sub.save()


def unsubscribe(user, path):
    """
    Unsubscribe a user from a path, blocking notices of updates on it.  This is not as simple as
    deleting the subscription object, rather it marks them unsubscribed so that futher subscriptions
    are ignored.
    """
    if isinstance(path, models.Model):
        path = model_sig(path)
    hits = Subscription.objects.filter(user=user, path=path).update(toggle=False)
    if hits == 0:
        Subscription.objects.create(user=user, path=path, toggle=False)

    return True


def is_subscribed(user, path):
    """
    Checks to see if a user is subscribed to the given path.
    """
    if isinstance(path, models.Model):
        path = model_sig(path)
    return Subscription.objects.filter(user=user, path=path, toggle=True).count() > 0


def get_subscribers(path):
    if isinstance(path, models.Model):
        path = model_sig(path)
    subscriptions = Subscription.objects.filter(path=path, toggle=True)
    return set([s.user for s in subscriptions])


def send_event(actor, type, path, **context):
    """
    Log an event performed by actor, of the type, on the path, and any other context arguments needed
    to render notification templates.
    """
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

    sub_path, _, _  = path.partition(':')

    # Find users to be notified
    users = get_subscribers(sub_path)

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
        if user.email == actor.email:
            continue
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



