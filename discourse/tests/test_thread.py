from django.test import TestCase
from discourse import event, follow
from django.contrib.auth import get_user_model

from discourse.uri import uri

from discourse.models import Comment, Vote



class TestEvent(TestCase):
    def setUp(self):
        self.actor = get_user_model()(username="deadwisdom", email="deadwisdom@", first_name='Dead', last_name="Wisdom")
        self.anchor = get_user_model()(username="place", email="place@", first_name='DA', last_name="PLACE")
        self.actor.save()
        self.anchor.save()

    def test_create_comment(self):
        comment = Comment.objects.create(anchor_uri=uri(self.anchor), body="HELLO", author=self.actor)

    def test_with_parent(self):
        comment = Comment.objects.create(anchor_uri=uri(self.anchor), body="HELLO", author=self.actor)
        comment = Comment.objects.create(anchor_uri=uri(self.anchor), body="HELLO TO YOU TOO", author=self.actor, parent=comment)

    def test_vote(self):
        comment = Comment.objects.create(anchor_uri=uri(self.anchor), body="HELLO", author=self.actor)
        self.assertEqual(comment.value, 1)

        comment.vote(self.actor, -1)
        comment.fix_value()

        self.assertEqual(comment.value, -1)

