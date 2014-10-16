from django.test import TestCase
from discourse import event, follow
from django.contrib.auth import get_user_model


RESULTS = {}

@event.on("join")
def on_join(e):
    RESULTS['on_join'] = e


@event.on_notify
def send_notifications(event, users):
    RESULTS['notify'] = users


class TestEvent(TestCase):
    def setUp(self):
        RESULTS.clear()
        self.actor = get_user_model()(username="deadwisdom", email="deadwisdom@", first_name='Dead', last_name="Wisdom")
        self.anchor = get_user_model()(username="place", email="place@", first_name='DA', last_name="PLACE")
        self.actor.save()

    def test_follow(self):
        follow.follow( self.actor, self.actor )
        e = event.publish('somewhere', self.actor, 'join')
        self.assertEqual(RESULTS['on_join'], e)
        self.assertEqual(RESULTS['notify'], set([self.actor]))

    def test_unfollow(self):
        follow.unfollow( self.actor, self.actor )
        e = event.publish('somewhere', self.actor, 'join')
        self.assertEqual(RESULTS.get('notify'), None)

    def test_follow_somewhere(self):
        follow.follow( self.actor, "somewhere" )
        e = event.publish('somewhere', self.actor, 'join')
        self.assertEqual(RESULTS['on_join'], e)
        self.assertEqual(RESULTS['notify'], set([self.actor]))

    def test_real_anchor(self):
        follow.follow( self.actor, self.anchor )
        e = event.publish(self.anchor, self.actor, 'join')
        self.assertEqual(RESULTS['on_join'], e)
        self.assertEqual(RESULTS['notify'], set([self.actor]))
        self.assertEqual(e.anchor, self.anchor)

