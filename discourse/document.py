import traceback
from django.db import models
from django.conf import settings
from django.utils.html import normalize_newlines, urlize
from django.template.loader import render_to_string
from django.template import Template, Context
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

import ttag
from yamlfield.fields import YAMLField
from cleaner import clean_html

from ajax import JsonResponse
from uri import *
from message import channel_for, on


class DocumentTemplate(models.Model):
    """
    Represents a template / structure of Documents.
    """
    slug = models.SlugField(primary_key=True)
    structure = YAMLField()

    def __unicode__(self):
        return self.slug

    class Meta:
        app_label = 'discourse'


class Document(models.Model):
    """
    Represents a content Document.
    """
    template = models.ForeignKey(DocumentTemplate, blank=True, null=True)
    anchor_uri = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.anchor_uri

    @property
    def url(self):
        return reverse("discourse:document", args=(self.anchor_uri,))

    def get_content(self, context=None):
        """
        Returns the content as a tree, see _content_tree()
        """
        if context is None:
            context = Context({})
        context['document'] = self
        if self.template:
            structure = self.template.structure
        else:
            structure = [{'content': 'Content'}]
        content_map = dict((c.attribute, c.body) for c in self.content.all())
        return self._content_tree(structure, content_map, context)

    def set_content(self, attribute, body):
        content, created = self.content.get_or_create(attribute=attribute, defaults={'body': body})
        if not created:
            content.body = body
            content.save()
        return content

    def _content_tree(self, structure, content_map, context):
        """
        Creates a tree of pages and sections within using the given ``structure`` and ``content_map``.
        
        Body is rendered as a template with the given context.

        e.g.
        [
            {'title': 'Page 1', 'is_empty': False, sections': [
                {'attribute': 'summary', 'title': 'Summary', 'html': '...', 'is_empty': False}
            ]},
            {'title': 'Page 2', 'is_empty': True, sections': [
                {'attribute': 'overview', 'title': 'Overview', 'html': '', 'is_empty': True}
            ]},
        ]
        """
        parts = []
        if not structure:
            return parts
        for part in structure:
            left, right = part.items()[0]
            if isinstance(right, list):
                sections = self._content_tree(right, content_map, context)
                is_empty = all(x['is_empty'] for x in sections)
                parts.append({'title': left, 'sections': sections, 'is_empty': is_empty})
            else:
                src = content_map.get(left, '')
                try:
                    html = Template(src).render(context)
                except Exception, e:
                    html = '<div class="template-error"><strong>Error rendering body</strong><br>%s: %s<br>%s</div>' % (e.__class__.__name__, e, traceback.format_exc())
                is_empty = not bool( html.strip() )
                parts.append({'attribute': left, 'title': right, 'html': html, 'src': src, 'is_empty': is_empty})
        return parts

    class Meta:
        app_label = 'discourse'


class DocumentContent(models.Model):
    """
    Content for a document.
    """
    document = models.ForeignKey(Document, related_name="content")
    attribute = models.SlugField()
    body = models.TextField()

    def __unicode__(self):
        return self.attribute

    def build(self, context=None):
        return {
            'attribute': self.attribute,
            'src': self.body,
            'html': self.render(context),
            'url': self.document.url,
        }

    def render(self, context):
        context = Context(context or {})
        context['document'] = self.document
        try:
            html = Template(self.body).render(context)
        except Exception, e:
            is_error = True
            html = '<div class="template-error"><strong>Error rendering body</strong><br>%s: %s<br>%s</div>' % (e.__class__.__name__, e, traceback.format_exc())
        return html

    class Meta:
        app_label = 'discourse'


### Template Tags ###
class DocumentTag(ttag.Tag):
    """
    Creates a document with multiple sections.
    """
    anchor = ttag.Arg(required=True)
    sub = ttag.Arg(default=None, keyword=True, required=False)          # Optional sub-document
    template = ttag.Arg(required=False, keyword=True)                   # Optional template name
    seed = ttag.Arg(default=None, keyword=True, required=False )        # Optional seed for the content
    plain = ttag.Arg(default=None, keyword=True, required=False)        # Optional render all the content plainly for search indexing
    
    class Meta:
        name = "document"

    def render(self, context):
        data = self.resolve(context)
        anchor = uri(data.get('anchor'), data.get('sub'))
        template = data.get('template')
        request = context.get('request')
        editable = False

        channel = channel_for(anchor)

        if hasattr(channel.get_anchor(), 'can_edit') and hasattr(request, 'user'):
            editable = channel.get_anchor().can_edit(request.user)

        if data.get('plain'):
            return "\n".join( [o.body for o in DocumentContent.objects.filter(document__anchor_uri=anchor)] )
        
        try:
            doc = Document.objects.filter(anchor_uri=anchor)[0]
        except IndexError:
            if template:
                template = DocumentTemplate.objects.get_or_create(slug=template)[0]
            else:
                template = None
            doc = Document.objects.create(anchor_uri=anchor, template=template)

        content = doc.get_content(context)

        context_vars = {'document': doc,
                        'content': content,
                        'anchor': anchor,
                        'is_empty': all([p['is_empty'] for p in content]),
                        'request': request}

        if request:
            try:
                m = channel.publish('view', request.user, data={'editable': editable})
                if not m:
                    return ""
            except PermissionDenied:
                return ""

            context_vars['editable'] = m.data['editable']

        if doc.template:
            return render_to_string(['discourse/document-%s.html' % doc.template.slug, 'discourse/document.html'], context_vars, context)
        else:
            return render_to_string('discourse/document.html', context_vars, context)



### Views ###
def manipulate(request, uri):
    document = get_object_or_404(Document, anchor_uri=uri)

    if not request.POST:
        return HttpResponseBadRequest()
    
    attribute = request.POST['attribute']
    value = clean_html(request.POST['value']).strip()

    if not channel_for(document).publish('update', request.user, data={'attribute': attribute, 'value': value}):
        raise PermissionDenied()

    if not value:
        document.content.filter(attribute=attribute).delete()
        return JsonResponse(None)

    content, created = document.content.get_or_create(attribute=attribute, defaults={'body': value})
    if not created:
        content.body = value
        content.save()

    return JsonResponse(content.build(locals()))


@on('document:edit')
def save_document(m):
    document = m.get_channel().get_document()
    source = m.data['source']
    attribute = m.data['attribute']

    if not source:
        document.content.filter(attribute=attribute).delete()
        return JsonResponse(None)

    content, created = document.content.get_or_create(attribute=attribute, defaults={'body': source})
    if not created:
        content.body = source
        content.save()

    m.data['_content'] = content.build(locals())
    #print m.pack()


#class DocumentType(models.Model):
#    name = models.CharField(max_length=255, unique=True)
#    source = models.TextField(blank=True, default="{{document.content}}")
#
#    def render(self, document, context):
#        template = Template(self.source)
#        context.push({'document': document})
#        try:
#            return template.render(context)
#        finally:
#            context.pop()
#
#
#class Document(models.Model):
#    subject_uri = models.CharField(max_length=255)
#    value = YAMLField()
#    type = models.ForeignKey(DocumentType, blank=True, null=True)
#    authors = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
#    modified = models.DateTimeField(auto_now=True)
#    created = models.DateTimeField(auto_now_add=True)
#    version = models.ForeignKey(Event, blank=True, null=True)
#
#    def __repr__(self):
#        return "Document(%r)" % self.subject_uri
#
#    def __getitem__(self, k):
#        if isinstance(self.value, dict):
#            return DocumentProperty(self, k, self.value.get(k, None))
#        else:
#            return DocumentProperty(self, k, None)
#
#    def update(self, value, author=None):
#        parent = self.version_id if self.version_id else None
#        e = publish("document-update", self.subject_uri, {'value': value, 'parent': parent}, author=author)
#        if e:
#            self.version = e
#
#            if isinstance(value, dict) and isinstance(self.value, dict):
#                self.value.update(value)
#            else:
#                self.value = value
#
#            self.save()
#            if author:
#                self.authors.add(author)
#            return e
#        else:
#            return None
#    
#    def render(self, context):
#        doctype = self.type or DocumentType("temporary")
#        return doctype.render(self, context)
#
#    def replay(self, target=None):
#        history = self.get_history()
#        value = None
#        for e in history:
#            if isinstance(e['value'], dict) and isinstance(value, dict):
#                value.update(e['value'])
#            else:
#                value = e['value']
#            if e['version'] == target:
#                break
#        return value
#
#    def get_history(self):
#        events = Event.get_for_object(self)
#        if not events:
#            return None
#        parent_map = dict((e.data['parent'], e) for e in events)
#        e = parent_map[None]
#        results = []
#        while e:
#            results.append(e)
#            e = parent_map[e.data['parent']]
#        return results
#
#
#class DocumentProperty(object):
#    def __init__(self, document, key, value, editable=False):
#        self.document = document
#        self.key = key
#        self.value = value
#        self.editable = editable
#
#    def __unicode__(self):
#        return render_to_string("discourse/document/property.html", self.__dict__)
#

