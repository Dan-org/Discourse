from django.test import TestCase
from discourse.models import Comment
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.test.client import Client
from django.core.mail import outbox


@override_settings(EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend')
class AnimalTestCase(TestCase):
    def setUp(self):
        # Create some users.
        self.users = {
            'bob': User.objects.create(username="bob", first_name="Bob", last_name="Tester"),
            'sally': User.objects.create(username="sally", first_name="Sally", last_name="Tester"),
            'dorthy': User.objects.create(username="dorth", first_name="Dorthy", last_name="Tester"),
        }
        for user in self.users.values():
            user.set_password('pass')
            user.save()

    def test_comments_exist(self):
        self.assertEqual(Comment.objects.count(), 0)

        c = Client()
        c.login(username='bob', password='pass')
        response = c.post('/discourse/thread/test/', {'body': 'comment 1 body'})

        assert(len(outbox) == 0)

        c = Client()
        c.login(username='bob', password='pass')
        response = c.post('/discourse/thread/test/', {'body': 'comment 2 body'})

        assert(len(outbox) == 0)

        c = Client()
        c.login(username='sally', password='pass')
        response = c.post('/discourse/thread/test/', {'body': 'comment 3 body'})

        self.assertEqual(len(outbox), 1)