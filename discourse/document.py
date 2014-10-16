from django.db import models
from django.conf import settings
from django.utils.html import normalize_newlines, urlize

from yamlfield import YAMLField


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
    template = models.ForeignKey(DocumentTemplate)
    anchor_uri = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.anchor_uri

    @property
    def url(self):
        return "/discourse/content/%s" % (self.anchor_uri)

    def get_content(self, context=None):
        """
        Returns the content as a tree, see _content_tree()
        """
        if context is None:
            context = Context({})
        context['document'] = self
        structure = self.template.structure
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

    def info(self, context=None):
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
