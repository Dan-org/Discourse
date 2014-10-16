from django.test import TestCase
from discourse import event, follow
from django.contrib.auth import get_user_model

from discourse.uri import uri

from discourse.models import Document



class TestDocument(TestCase):
    def setUp(self):
        self.actor = get_user_model()(username="deadwisdom", email="deadwisdom@", first_name='Dead', last_name="Wisdom")
        self.anchor = get_user_model()(username="place", email="place@", first_name='DA', last_name="PLACE")
        self.actor.save()
        self.anchor.save()

    def test_create_document(self):
        pass
