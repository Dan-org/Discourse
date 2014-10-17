from django.test import TestCase as DjangoTestCase, Client
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.template.loader import Template, Context

from discourse.uri import uri
from discourse.event import on, on_notify


class MockRequest(object):
    def __init__(self, user):
        self.user = user


class TestCase(DjangoTestCase):
    def setUp(self):
        self.actor = get_user_model()(username="deadwisdom", email="deadwisdom@", first_name='Dead', last_name="Wisdom")
        self.actor.set_password('pass')
        self.actor.save()

        self.anchor = get_user_model()(username="place", email="place@", first_name='DA', last_name="PLACE")
        self.anchor.save()

        self.client = Client()
        self.client.login(username="deadwisdom", password="pass")

        self.request = MockRequest(self.actor)

        self.events = []
        self.last_event = None
        self.last_notify = None

        @on("*")
        def on_event(e):
            self.events.append(e)
            self.last_event = e

        @on_notify
        def on_notifier(e, users):
            self.last_notify = users


    def ajax_post(self, url, data, **kwargs):
        return self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest', **kwargs)
    
    def ajax_get(self, url, data, **kwargs):
        return self.client.get(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest', **kwargs)


def url_for(view, *args, **kwargs):
    args = (uri(a) for a in args)
    kwargs = dict((k, uri(v)) for k, v in kwargs.items())
    return reverse('discourse:%s' % view, args=args, kwargs=kwargs)


ajax = dict(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
