from base import *

from discourse.uri import uri
from discourse.models import Subscription
from discourse import follow, unfollow, publish


class TestFollow(TestCase):
    def test_follow_actor(self):
        follow( self.actor, self.actor )
        e = publish('somewhere', self.actor, 'join')
        self.assertEqual(self.last_notify, set([self.actor]))

    def test_follow_anchor(self):
        follow( self.actor, self.anchor )
        e = publish(self.anchor, self.actor, 'join')
        self.assertEqual(self.last_notify, set([self.actor]))

    def test_not_follow(self):
        e = publish('somewhere', self.actor, 'join')
        self.assertEqual(self.last_notify, None)

    def test_unfollow(self):
        unfollow( self.actor, self.actor )
        e = publish('somewhere', self.actor, 'join')
        self.assertEqual(self.last_notify, None)

    def test_follow_somewhere(self):
        follow( self.actor, "somewhere" )
        e = publish('somewhere', self.actor, 'join')
        self.assertEqual(self.last_notify, set([self.actor]))

    def test_view(self):
        target = uri(self.anchor)
        self.ajax_post(reverse('discourse:follow'), {'uri': target})
        e = publish(self.anchor, self.actor, 'join')
        self.assertEqual(self.last_notify, set([self.actor]))

        self.last_notify = None

        target = uri(self.anchor)
        self.ajax_post(reverse('discourse:follow'), {'uri': target, 'unfollow': 'true'})
        e = publish(self.anchor, self.actor, 'join')
        self.assertEqual(self.last_notify, None)

    