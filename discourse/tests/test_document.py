from base import *
from django.contrib.auth import get_user_model
from django.template import Context, Template

from discourse.uri import uri

from discourse.models import Document



class TestDocument(TestCase):
    def test_create_document(self):
        d = Document.objects.create(anchor_uri=uri(self.anchor))
        d.set_content("content", "DOCUMENT CONTENT")
        self.assertEqual( d.get_content(Context({}))[0]['html'], "DOCUMENT CONTENT" )

    def test_tag(self):
        self.request = MockRequest(self.actor)
    
        result = Template("""{% load discourse %}
            {% document anchor %}
        """).render(Context(self.__dict__))

        result = Template("""{% load discourse %}
            {% document anchor template="simple"%}
        """).render(Context(self.__dict__))

    def test_update(self):
        d = Document.objects.create(anchor_uri=uri(self.anchor))
        d.set_content("content", "DOCUMENT CONTENT")
        self.assertEqual( d.get_content(Context({}))[0]['html'], "DOCUMENT CONTENT" )

        response = self.ajax_post(d.url, {'attribute': 'content', 'value': 'NEW DOCUMENT CONTENT'})
        self.assertEqual(response.status_code, 200)

        d = Document.objects.get(anchor_uri=uri(self.anchor))
        self.assertEqual( d.get_content(Context({}))[0]['html'], "NEW DOCUMENT CONTENT" )

        self.request = MockRequest(self.actor)
        result = Template("""{% load discourse %}
            {% document anchor %}
        """).render(Context(self.__dict__))
        
        assert "NEW DOCUMENT CONTENT" in result

    def test_update_fail(self):
        d = Document.objects.create(anchor_uri=uri(self.anchor))
        d.set_content("content", "DOCUMENT CONTENT")

        @on('document')
        def fail_document(e):
            return False

        response = self.ajax_post(d.url, {'attribute': 'content', 'value': 'NEW DOCUMENT CONTENT'})
        self.assertEqual(response.status_code, 403)

