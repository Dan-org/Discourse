from django.test import TestCase
from discourse.models import Comment
from django.contrib.auth import get_user_model


class TestNoticesYo(TestCase):
    def setUp(self):
        author = get_user_model()(email="deadwisdom@")
        Comment.objects.create(path="url:/", body="comment 1 body", )
        Animal.objects.create(name="lion", sound="roar")
        Animal.objects.create(name="cat", sound="meow")

    def test_animals_can_speak(self):
        """Animals that can speak are correctly identified"""
        lion = Animal.objects.get(name="lion")
        cat = Animal.objects.get(name="cat")
        self.assertEqual(lion.speak(), 'The lion says "roar"')
        self.assertEqual(cat.speak(), 'The cat says "meow"')
