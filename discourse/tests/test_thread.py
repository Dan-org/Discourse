from base import *

from discourse.uri import *
from discourse import event, follow
from discourse.models import Comment, Vote


class TestEvent(TestCase):
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

    def test_tag(self):
        self.request = MockRequest(self.actor)
        result = Template("""{% load discourse %}
            {% thread anchor %}
        """).render(Context(self.__dict__))

        self.request = MockRequest(self.actor)
        result = Template("""{% load discourse %}
            {% thread anchor scored=True %}
        """).render(Context(self.__dict__))

    def test_create_comment(self):
        response = self.ajax_post(url_for('thread', self.anchor), {'body': 'POSTED'})
        self.assertEqual(response.status_code, 200)
        pk = response.data['id']

        comment = Comment.objects.get(pk=pk)
        self.assertEqual(comment.body, 'POSTED')
        self.assertEqual(comment.parent, None)

    def test_edit_comment(self):
        comment = Comment.objects.create(anchor_uri=uri(self.anchor), body="HELLO", author=self.actor)

        response = self.ajax_post(url_for('thread', self.anchor), {'body': 'POSTED', 'id': comment.id})
        self.assertEqual(response.data['id'], comment.id)
        
        comment = Comment.objects.get(pk=comment.id)
        self.assertEqual(comment.body, 'POSTED')
        self.assertEqual(comment.parent, None)

    def test_delete_comment(self):
        comment = Comment.objects.create(anchor_uri=uri(self.anchor), body="HELLO", author=self.actor)

        response = self.ajax_post(url_for('thread', self.anchor), {'id': comment.id, 'delete': 'yes'})
        self.assertEqual(response.data['id'], None)
        
        self.assertRaises(Comment.DoesNotExist, Comment.objects.get, pk=comment.id)

    
