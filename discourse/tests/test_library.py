from cStringIO import StringIO

from base import *
from discourse import event, follow
from django.contrib.auth import get_user_model
from django.core.files import File

from discourse.uri import uri

from discourse.models import Attachment
from test_thread import MockRequest, Template, Context

class TestLibrary(TestCase):
    def test_create_attachment(self):
        attachment = Attachment.objects.create(
            author = self.actor, 
            anchor_uri = uri(self.anchor),
            filename = "pictures/thing.png",
            content_type = "image/png",
        )

        self.assertEqual(attachment.hidden, False)
        self.assertEqual(attachment.featured, False)

    def test_tag(self):
        self.request = MockRequest(self.actor)
        result = Template("""{% load discourse %}
            {% library anchor %}
        """).render(Context(self.__dict__))

        assert "/discourse/library/auth/user/%s" % self.anchor.id in result

    def test_upload(self):
        filename = "attachment.txt"

        file = File(StringIO("THIS IS THE ATTACHMENT"))
        file.name = 'the-text.txt'
        file.content_type = "text/plain"

        url = url_for('library', self.anchor) + '/' + filename

        response = self.ajax_post(url, {'attachment': file})
        self.assertEqual(response.status_code, 200)
        pk = response.data['id']
        content_type = response.data['content_type']

        self.assertEqual(content_type, 'text/plain')

        Attachment.objects.get(anchor_uri=uri(self.anchor), filename=filename)

    def test_upload_without_filename_in_url(self):
        filename = "attachment.txt"

        file = File(StringIO("THIS IS THE ATTACHMENT"))
        file.name = 'the-text.txt'
        file.content_type = "text/plain"

        url = url_for('library', self.anchor)

        response = self.ajax_post(url, {'attachment': file, 'filename': filename})
        self.assertEqual(response.status_code, 200)
        pk = response.data['id']
        content_type = response.data['content_type']

        self.assertEqual(content_type, 'text/plain')

        Attachment.objects.get(anchor_uri=uri(self.anchor), filename=filename)

    def test_edit(self):
        attachment = Attachment.objects.create(
            author = self.actor, 
            anchor_uri = uri(self.anchor),
            filename = "pictures/thing.png",
            content_type = "image/png",
        )

        response = self.ajax_post(attachment.url, {'filename': 'other.png'})
        self.assertEqual(response.data['filename'], 'other.png')
        url = response.data['url']

        self.ajax_post(url, {'hidden': 'true'})        
        attachment = Attachment.objects.get(filename='other.png', anchor_uri=uri(self.anchor))
        self.assertEqual(attachment.hidden, True)

        self.ajax_post(url, {'featured': 'true'})        
        attachment = Attachment.objects.get(filename='other.png', anchor_uri=uri(self.anchor))
        self.assertEqual(attachment.featured, True)

    def test_delete(self):
        attachment = Attachment.objects.create(
            author = self.actor, 
            anchor_uri = uri(self.anchor),
            filename = "pictures/thing.png",
            content_type = "image/png",
        )

        response = self.ajax_post(attachment.url, {'delete': 'yes'})
        self.assertRaises(Attachment.DoesNotExist, Attachment.objects.get, filename='pictures/thing.png', anchor_uri=uri(self.anchor))

    def test_download(self):
        filename = "attachment.txt"

        file = File(StringIO("THIS IS THE ATTACHMENT"))
        file.name = 'the-text.txt'
        file.content_type = "text/plain"

        url = url_for('library', self.anchor) + '/' + filename
        
        self.ajax_post(url, {'attachment': file})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        assert response['Location'].startswith('http://testserver/media/attachments/the-text')

    def test_add_link(self):
        url = url_for('library', self.anchor)

        response = self.ajax_post(url, {'link': "http://google.com"})
        self.assertEqual(response.status_code, 200)
        pk = response.data['id']
        filename = response.data['filename']
        content_type = response.data['content_type']

        self.assertEqual(content_type, 'text/url')

        attachment = Attachment.objects.get(anchor_uri=uri(self.anchor), filename=filename)

        response = self.client.get(attachment.url)
        self.assertEqual(response.status_code, 302)
        assert response['Location'] == 'http://google.com'

    

