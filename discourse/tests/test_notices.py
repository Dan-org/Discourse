from django.test import TestCase
from discourse.models import Comment
from django.contrib.auth import get_user_model


class TestNoticesYo(TestCase):
    def _setUp(self):
        author = get_user_model()(email="deadwisdom@")
        Comment.objects.create(path="url:/", body="comment 1 body", author=author)


