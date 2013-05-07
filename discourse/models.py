import posixpath

from yamlfield import YAMLField

from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.urlresolvers import reverse


### Helpers ###
def model_sig(instance):
    cls = instance.__class__
    name = cls._meta.module_name
    app = cls._meta.app_label
    pk = instance._get_pk_val()
    return "%s/%s/%s" % (app, name, pk)


### Tags ###
class Comment(models.Model):
    path = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    created = models.DateTimeField(auto_now_add=True)
    deleted = models.DateTimeField(blank=True, null=True)
    edited = models.DateTimeField(blank=True, null=True)

    def __repr__(self):
        return "Comment(%r, %d)" % (self.path, self.id)

    def __unicode__(self):
        return repr(self)

    def info(self):
        return {
            'path': self.path,
            'body': self.body,
            'author': str(self.author),
            'created': self.created,
            'edited': self.edited
        }

    class Meta:
        ordering = ('path', 'id')

    @property
    def url(self):
        return reverse("discourse:thread", args=[self.path])
    
    @classmethod
    def get_thread(cls, path):
        """
        Returns a QuerySet of the media in the given ``path``.
        """
        return cls._default_manager.filter(path=path).order_by('id')


class Attachment(models.Model):
    path = models.CharField(max_length=255)         # Too small?  Probably.
    mimetype = models.CharField(max_length=255)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    caption = models.TextField(blank=True)
    featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0)
    file = models.FileField(upload_to="attachments")

    @property
    def url(self):
        return "/discourse/attachments/%s" % (self.path)

    @property
    def filename(self):
        return posixpath.basename(self.path)

    def info(self):
        return {
            'id': self.id,
            'path': self.path,
            'content_type': self.mimetype,
            'caption': self.caption,
            'order': self.order,
            'filename': self.filename,
            'url': self.url
        }

    def __unicode__(self):
        return self.path

    def __repr__(self):
        return "Attachment(%r)" % (self.path)

    @classmethod
    def get_folder(cls, path):
        """
        Returns a QuerySet of the media in the given ``path`` folder.
        """
        if not path.endswith('/'):
            path = path + '/'
        return cls._default_manager.filter(path__startswith=path)


class DocumentTemplate(models.Model):
    """
    Represents a template / structure of Documents.
    """
    slug = models.SlugField(primary_key=True)
    structure = YAMLField()

    def __unicode__(self):
        return self.slug


class Document(models.Model):
    """
    Represents a content Document.
    """
    template = models.ForeignKey(DocumentTemplate)
    path = models.CharField(max_length=255)
    
    def __unicode__(self):
        return self.path

    @property
    def url(self):
        return "/discourse/content/%s" % (self.path)

    def get_content(self):
        """
        Returns the content as a tree, see _content_tree()
        """
        structure = self.template.structure
        content_map = dict((c.attribute, c.body) for c in self.content.all())
        return self._content_tree(structure, content_map)

    def _content_tree(self, structure, content_map):
        """
        Creates a tree of pages and sections within using the given ``structure`` and ``content_map``.
        
        e.g.
        [
            {'title': 'Page 1', 'is_empty': False, sections': [
                {'attribute': 'summary', 'title': 'Summary', 'body': '...', 'is_empty': False}
            ]},
            {'title': 'Page 2', 'is_empty': True, sections': [
                {'attribute': 'overview', 'title': 'Overview', 'body': '', 'is_empty': True}
            ]},
        ]
        """
        parts = []
        for part in structure:
            left, right = part.items()[0]
            if isinstance(right, list):
                sections = self._content_tree(right, content_map)
                is_empty = all(x['is_empty'] for x in sections)
                parts.append({'title': left, 'sections': sections, 'is_empty': is_empty})
            else:
                body = content_map.get(left, '')
                is_empty = not bool( body.strip() )
                parts.append({'attribute': left, 'title': right, 'body': body, 'is_empty': is_empty})
        return parts



class DocumentContent(models.Model):
    """
    Content for a document.
    """
    document = models.ForeignKey(Document, related_name="content")
    attribute = models.SlugField()
    body = models.TextField()
    #author = models.ForeignKey(settings.AUTH_USER_MODEL)
    #modified = models.DateTimeField()

    def __unicode__(self):
        return self.attribute

    def info(self):
        return {
            'attribute': self.attribute,
            'body': self.body,
            'url': self.document.url,
        }

#    def save(self, *args, **kwargs):
#        try:
#            zero = self.deltas.get()
#        except DocumentContent.DoesNotExist:
#            zero = DocumentContent(attribute=attribute, version=0, body="")
#        delta = difflib.diff(zero.body, body)
#
#
#class DocumentDelta(models.Model):
#    content = models.ForeignKey(DocumentContent, related_name="deltas")
#    version = models.PositiveIntegerField()
#    diff = models.TextField()
#    author = models.ForeignKey(settings.AUTH_USER_MODEL)
#    created = models.DateTimeField(auto_now_add=True)
#
#    def __unicode__(self):
#        return "DocumentDelta(version=%s)" % self.version