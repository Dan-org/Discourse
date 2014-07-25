import urllib
import ttag
import json
import re

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.template import Template
from django.utils.safestring import mark_safe
from django.conf import settings
from django.db import models
from django import template

from ..models import Comment, Attachment, Document, DocumentContent, DocumentTemplate, Stream, model_sig, document_view, library_view
from ..notice import is_subscribed


### Helpers ###
def unique_list(seq):
    """Turns sequence into a list of unique items, while perserving order."""
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def get_path(context, path, sub=None):
    """Returns a real path for the given path."""
    if path is None:
        try:
            return "url:" + urllib.quote( context['request'].get_full_path() )
        except KeyError:
            raise RuntimeError('Template context lacks a "request" object to get the path from, please provide a path to the templatetag.')
    elif isinstance(path, models.Model):
        path = model_sig(path)
    if sub:
        path = "%s:%s" % (path, sub)
    return path


def get_path_list(context, parts):
    """Returns a real path for the given path parts."""
    path = []
    for part in parts:
        if isinstance(part, models.Model):
            path.append( model_sig(part) )
        else:
            path.append( part )
    if path:
        return ":".join(path)
    return "url:" + urllib.quote( context['request'].get_full_path() )


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

    Also, add up and down voting.
        {% thread instance scored=True %}

    See ``discourse/models.py`` on options to change how comments are rendered.
    """
    path = ttag.Arg(required=False)                                     # Path or model for the comment thread.
    sub = ttag.Arg(default=None, keyword=True, required=False)          # The sub-thread
    depth = ttag.Arg(default=2, keyword=True)                           # Depth of the comments.
    scored = ttag.Arg(default=False, keyword=True)                      # Whether or not to score the comments.
    template = ttag.Arg(default=None, keyword=True, required=False)     # The template to use for rendering the comments.

    def render(self, context):
        data = self.resolve(context)
        path = get_path(context, data.get('path'), data.get('sub'))
        scored = (data.get('scored') == True)
        comments = Comment.get_thread(path, context.get('request').user)
        template = data.get('template') or 'discourse/thread.html'

        return render_to_string(template, {'comments': comments, 
                                           'path': path,
                                           'depth': data.get('depth'),
                                           'scored': scored,
                                           'auth_login': settings.LOGIN_REDIRECT_URL}, context)
    class Meta:
        name = "thread"


class ThreadCountTag(ttag.Tag):
    """
    Returns the count of comments.
    """
    path = ttag.Arg(required=False)                                     # Path or model for the comment thread.
    sub = ttag.Arg(default=None, keyword=True, required=False)          # The sub-thread
    parent = ttag.Arg(default=None, keyword=True, required=False)       # Only count comments below this one

    def render(self, context):
        data = self.resolve(context)
        path = get_path(context, data.get('path'), data.get('sub'))
        parent = data.get('parent')
        scored = bool( data.get('scored') )
        if parent:
            count = Comment.objects.filter(path=path, deleted__isnull=True, parent=parent).count()
        else:
            count = Comment.objects.filter(path=path, deleted__isnull=True).count()
        if count == 0:
            return ""
        elif count == 1:
            return "1 Comment"
        else:
            return "%d Comments" % count

    class Meta:
        name = "threadcount"


class Library(ttag.Tag):
    """
    Creates a media library for the given object or current page.
    """
    path = ttag.Arg(required=False)

    def render(self, context):
        data = self.resolve(context)
        request = context['request']
        path = get_path(context, data.get('path'))
        attachments = Attachment.get_folder(path)
        context['library'] = path

        context_vars = {'attachments': attachments,
                        'path': path,
                        'hidden': False,
                        'is_empty': False,
                        'request': request,
                        'editable': request.user.is_superuser}

        try:
            library_view.send(sender=Attachment, request=request, context=context_vars)
        except PermissionDenied:
            context_vars['hidden'] = True

        if context_vars['hidden']:
            return ""

        context_vars['json'] = json.dumps([a.info() for a in attachments])
        
        return render_to_string('discourse/library.html', context_vars, context)


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

    Create a frame with only the featured images in the library:

        {% frame featured=True %}
    """
    path = ttag.MultiArg()
    width = ttag.Arg(required=False, keyword=True)
    height = ttag.Arg(required=False, keyword=True)
    class_ = ttag.Arg(required=False, keyword=True)
    featured = ttag.Arg(required=False, keyword=True)

    def render(self, context):
        data = self.resolve(context)
        request = context['request']
        width = data.get('width')
        height = data.get('height')
        featured = data.get('featured')
        cls = data.get('class_')
        path = get_path_list(context, data.get('path'))
        attachments = Attachment.get_folder(path)
        context['library'] = path

        if (featured):
            attachments = attachments.filter(featured=True)

        context_vars = {'attachments': attachments,
                        'path': path,
                        'width': width,
                        'height': height,
                        'class_': cls,
                        'hidden': False,
                        'request': request,
                        'editable': request.user.is_superuser}

        try:
            library_view.send(sender=Attachment, request=request, context=context_vars)
        except PermissionDenied:
            context_vars['hidden'] = True

        return render_to_string('discourse/frame.html', context_vars, context)


class DocumentTag(ttag.Tag):
    """
    Creates a document with multiple sections.
    """
    path = ttag.Arg(required=False)
    sub = ttag.Arg(default=None, keyword=True, required=False)          # Optional sub-document
    template = ttag.Arg(required=False, keyword=True)                   # Optional template name
    seed = ttag.Arg(default=None, keyword=True, required=False )        # Optional seed for the content
    plain = ttag.Arg(default=None, keyword=True, required=False)        # Optional render all the content plainly for search indexing

    def get_default_template(self, path, template=None):
        if template:
            try:
                return DocumentTemplate.objects.get(slug=template)
            except DocumentTemplate.DoesNotExist:
                return DocumentTemplate.objects.create(
                    slug=template,
                    structure="- content: Content",
                )
        try:
            return DocumentTemplate.objects.all()[0]
        except IndexError:
            return DocumentTemplate.objects.create(
                slug="simple",
                structure="- content: Content",
            )

    def render(self, context):
        data = self.resolve(context)
        path = get_path(context, data.get('path'), data.get('sub'))
        template = data.get('template')

        if data.get('plain'):
            return "\n".join( [o.body for o in DocumentContent.objects.filter(document__path=path)] )

        request = context['request']
        context['path'] = path

        try:
            doc = Document.objects.get(path=path)
        except Document.DoesNotExist:
            doc = Document.objects.create(path=path, template=self.get_default_template(path, template))

        content = doc.get_content(context)

        context_vars = {'document': doc,
                        'content': content,
                        'path': path,
                        'hidden': False,
                        'is_empty': all([p['is_empty'] for p in content]),
                        'request': request,
                        'editable': request.user.is_superuser}

        try:
            document_view.send(sender=doc, request=request, context=context_vars)
        except PermissionDenied:
            context_vars['hidden'] = True

        if context_vars['hidden']:
            return ""

        return render_to_string(['discourse/document-%s.html' % doc.template.slug, 'discourse/document.html'], context_vars, context)

    class Meta:
        name = "document"


### Stream ###
class StreamTag(ttag.Tag):
    """
    Show a stream for an object
    {% stream object %}

    Show a stream for a string
    {% stream 'pandas' %}

    Set the initial size of shown events to 5 instead of the default of 10:
    {% stream object size=5 %}

    Allow comments
    {% stream object comments=True %}
    """
    path = ttag.Arg(required=False)
    size = ttag.Arg(required=False, keyword=True)
    comments = ttag.Arg(required=False, keyword=True)

    def render(self, context):
        data = self.resolve(context)
        path = get_path(context, data.get('path'))
        request = context['request']
        size = data.get('size', 10)
        comments = data.get('comments', False)

        try:
            stream = Stream.objects.get(path=path)
            events = stream.events.all().order_by('-id')[:size]
            count = stream.events.count()
        except Stream.DoesNotExist:
            stream = Stream(path=path)
            events = ()
            count = 0

        return render_to_string('discourse/stream.html', {'stream': stream, 
                                                          'events': events,
                                                          'count': count,
                                                          'size': size,
                                                          'path': path, 
                                                          'auth_login': settings.LOGIN_REDIRECT_URL}, context)

    class Meta:
        name = "stream"


class EditableTag(ttag.Tag):
    """
    Outputs a property of an model object in such a way so that it can be edited live, very easily.
    """
    object = ttag.Arg(required=True)
    property = ttag.Arg(required=True)
    default = ttag.Arg(required=False, keyword=True)

    class Meta:
        name = "editable"

    def render(self, context):
        data = self.resolve(context)
        object = data['object']
        property = unicode(data['property'])
        default = data.get('default', None)
        value = getattr(object, property, default)
        path = get_path(context, object)
        field = object.__class__._meta.get_field_by_name(property)
        
        return render_to_string('discourse/editable.html', {'value': value, 
                                                            'object': object,
                                                            'property': property,
                                                            'default': default,
                                                            'path': path, 
                                                            'auth_login': settings.LOGIN_REDIRECT_URL}, context)


class Path(ttag.Tag):
    """
    Returns the discourse path associated with the object given as the first argument.
    """
    object = ttag.Arg(required=True)

    class Meta:
        name = "discourse_path"

    def render(self, context):
        data = self.resolve(context)
        object = data['object']
        return get_path(context, object)


class Subscriber(ttag.Tag):
    """
    Creates a subscribe button for the given path
    """
    object = ttag.Arg(required=True)

    class Meta:
        name = "subscriber"

    def render(self, context):
        data = self.resolve(context)
        object = data['object']
        request = context['request']
        path = get_path(context, object)
        url = reverse("discourse:subscribe")
        if request.user.is_authenticated():
            subscribed = is_subscribed(request.user, path)
        else:
            subscribed = False
        return render_to_string('discourse/subscriber.html', locals())



### Register ###
register = template.Library()
register.tag(ThreadTag)
register.tag(ThreadCountTag)
register.tag(Library)
register.tag(Frame)
register.tag(DocumentTag)
register.tag(StreamTag)
register.tag(EditableTag)
register.tag(Path)
register.tag(Subscriber)


### Filters ###
@register.filter(is_safe=True)
def to_json(value):
    return mark_safe(json.dumps(value))


re_hash = re.compile(r'\#\w[-_\w]+\w')
def hash_link(m):
    tag = m.group(0)
    return '<a href="/search/?q=%s">%s</a>' % (urllib.quote(tag), tag)

@register.filter(is_safe=True)
def hashtags(value):
    return mark_safe( re_hash.sub(hash_link, value) )


