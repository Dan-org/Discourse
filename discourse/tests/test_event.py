from base import *
from discourse import publish, follow, Event, on
from django.contrib.auth import get_user_model
from django.template import Context, Template


class TestEvent(TestCase):
    def test_real_anchor(self):
        e = publish(self.anchor, self.actor, 'join')
        self.assertEqual(self.last_event, e)
        self.assertEqual(e.anchor, self.anchor)
        self.assertEqual(e.actor, self.actor)

    def test_tag(self):
        result = Template("""{% load discourse %}
            {% follow anchor %}
        """).render(Context(self.__dict__))

    def test_views(self):
        self.request = MockRequest(self.actor)

        self.actor.is_superuser = True
        self.actor.save()
        
        self.client.get(reverse("discourse:monitor"))