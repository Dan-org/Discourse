import posixpath

from datetime import datetime
from yamlfield import YAMLField

from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.urlresolvers import reverse
from django.dispatch import Signal, receiver
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string


### Helpers ###
def model_sig(instance):
    cls = instance.__class__
    name = cls._meta.module_name  # activity
    app = cls._meta.app_label     # loft
    pk = instance._get_pk_val()   # 7
    return "%s/%s/%s" % (app, name, pk)

    "loft/activity/7"


### Events ###
comment_pre_edit = Signal(['request', 'action'])
comment_post_edit = Signal(['request', 'action'])

attachment_pre_edit = Signal(['request', 'action'])
attachment_post_edit = Signal(['request', 'action'])

document_pre_edit = Signal(['request', 'action'])
document_post_edit = Signal(['request', 'action'])


### Tags ###
class Comment(models.Model):
    path = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    created = models.DateTimeField(auto_now_add=True)
    deleted = models.DateTimeField(blank=True, null=True)
    edited = models.DateTimeField(blank=True, null=True)

    def __repr__(self):
        return "Comment(%r, %s)" % (self.path, self.id)

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

    def edit_by_request(self, request, body):
        self.body = body
        self.edited = datetime.now()
        comment_pre_edit.send(sender=self, request=request, action='edit')
        self.save()
        comment_post_edit.send(sender=self, request=request, action='edit')
        return self

    def delete_by_request(self, request):
        self.deleted = datetime.now()
        comment_pre_edit.send(sender=self, request=request, action='delete')
        self.save()
        comment_post_edit.send(sender=self, request=request, action='delete')
        return self

    @classmethod
    def create_by_request(cls, request, path, body):
        path = path.rstrip('/')
        comment = cls(path=path, body=body, author=request.user)
        comment_pre_edit.send(sender=comment, request=request, action='create')
        comment.save()
        comment_post_edit.send(sender=comment, request=request, action='create')
        return comment

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
        return cls._default_manager.filter(path=path, deleted__isnull=True).order_by('id')


@receiver(comment_pre_edit)
def check_author(sender, request, action, **kwargs):
    if action == 'edit' or action == 'delete':
        if request.user != sender.author and not request.user.is_superuser:
            raise PermissionDenied()


@receiver(comment_post_edit)
def notify_on_comment(sender, request, action, **kwargs):
    if action == 'create':
        #notify(sender.path, "comment", sender)
        pass


class Subscription(models.Model):
    path = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    toggle = models.BooleanField(default=True)

    def send(self, actor, type, **args):
        context = args.copy()
        context['actor'] = actor
        context['type'] = type
        context['path'] = self.path
        context['user'] = self.user
        subject = render_to_string("discourse/notifications/%s.subject.txt" % type, context)
        html = render_to_string("discourse/notifications/%s.html" % type, context)
        text = render_to_string("discourse/notifications/%s.txt" % type, context)
        to = [self.user.email]
        send_notification_email(to, subject, html, text)
    
    def __example__(self):
        notify(request.user, comment.path, "comment", comment=comment)
        notify(request.user, attachment.library, "upload", attachment=attachment)
        notify(request.user, comment.path, "document", sender)
        notify(request.user, model_sig(critique.report), "feedback", critique)


def notify(actor, path, type, **args):
    for sub in Subscription.objects.filter(path=path).exclude(user=actor):
        sub.send(actor, type, **args)

def subscribe(user, path):
    Subscription.objects.get_or_create(user=user, path=path)

def unsubscribe(user, path):
    hits = Subscription.objects.filter(user=user, path=path).update(toggle=False)
    if hits == 0:
        Subscription.objects.create(user=user, path=path, toggle=False)


#class Message(models.Model):
#    recipient = models.ForeignKey(settings.AUTH_USER_MODEL)
#    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)
#    type = models.SlugField()
#    path = models.CharField(max_length=255)
#
    


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

    def set_content(self, attribute, body):
        content, created = self.content.get_or_create(attribute=attribute, defaults={'body': body})
        if not created:
            content.body = body
            content.save()
        return content

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