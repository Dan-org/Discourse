import urllib
import ttag

from django.template.loader import render_to_string
from django.template import Template
from django.conf import settings
from django.db import models
from django import template

from ..models import Comment, Attachment, Document, DocumentTemplate, model_sig


### Helpers ###
def unique_list(seq):
    """Turns sequence into a list of unique items, while perserving order."""
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def get_path(context, path):
    """Returns a real path for the given path."""
    if path is None:
        try:
            return "/_url" + urllib.quote( context['request'].get_full_path() )
        except KeyError:
            raise RuntimeError('Template context lacks a "request" object to get the path from, please provide a path to the templatetag.')
    elif isinstance(path, models.Model):
        return model_sig(path)
    return path


### Tags ###
class ThreadTag(ttag.Tag):
    """
    Creates a thread of comments.  

    Usage:
    Create a list of comments based on the url of the page being viewed:
        
        {% thread %}

    Create a list of comments for the string "pandas":
        
        {% thread "pandas" %}

    Create a list of comments for a model instance which maps to the string 
    <instance.__class__.__name__.lower()>-<instance private key>, e.g. "post-2".

        {% thread instance %}

    See ``discourse/models.py`` on options to change how comments are rendered.
    """
    path = ttag.Arg(required=False)
    depth = ttag.Arg(default=2, keyword=True)

    def render(self, context):
        data = self.resolve(context)
        path = get_path(context, data.get('path'))
        comments = Comment.get_thread(path)
        return render_to_string('discourse/thread.html', {'comments': comments, 
                                                          'path': path, 
                                                          'auth_login': settings.LOGIN_REDIRECT_URL}, context)

    class Meta:
        name = "thread"


class Library(ttag.Tag):
    """
    Creates a media library for the given object or current page.
    """
    path = ttag.Arg(required=False)

    def render(self, context):
        data = self.resolve(context)
        path = get_path(context, data.get('path'))
        attachments = Attachment.get_folder(path)
        context['library'] = path
        return render_to_string('discourse/library.html', {'attachments': attachments, 'path': path}, context)


class AttachmentUrl(ttag.Tag):
    """
    Returns the url to an attachment given by the path.  Assumes a 'library' variable in the context.
    """
    path = ttag.Arg(required=False)

    def render(self, context):
        data = self.resolve(context)
        library = context['library']
        path = data.get('path')


class Frame(ttag.Tag):
    """
    Creates a media frame.  The frame will use an attachment library to display media.

    Create a frame for the current page with width 500:

        {% frame width=500 %}

    Create a frame for an attachment library of model instance with width 500.

        {% frame instance width=500 %}

    Create a frame with height 300:

        {% frame width=500 %}

    Create a frame with width 960 and height 540:

        {% frame width=960 height=540 %}

    Create a frame with a class of "big-image":

        {% frame class="big-image" %}
    """
    library = ttag.Arg(required=False)
    width = ttag.Arg(required=False, keyword=True)
    height = ttag.Arg(required=False, keyword=True)
    class_ = ttag.Arg(required=False, keyword=True)

    def render(self, context):
        data = self.resolve(context)
        return data


class DocumentTag(ttag.Tag):
    """
    Creates a document with multiple sections.
    """
    path = ttag.Arg(required=False)

    def render(self, context):
        data = self.resolve(context)
        path = get_path(context, data.get('path'))
        try:
            doc = Document.objects.get(path=path)
        except Document.DoesNotExist:
            doc = Document.objects.create(path=path, template=DocumentTemplate.objects.all()[0])
        return render_to_string(['discourse/document-%s.html' % doc.template.slug, 'discourse/document.html'], {'document': doc, 'content': doc.get_content(), 'path': path}, context)

    class Meta:
        name = "document"


### Register ###
register = template.Library()
register.tag(ThreadTag)
register.tag(Library)
register.tag(Frame)
register.tag(DocumentTag)
