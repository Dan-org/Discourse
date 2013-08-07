import re
import posixpath

from datetime import datetime
from yamlfield import YAMLField

from django.db import models
from django.utils.text import slugify
from django.conf import settings
from django.core.urlresolvers import reverse
from django.dispatch import Signal, receiver
from django.db.models.loading import get_model
from django.conf import settings
from django.template import Context, RequestContext, Template
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.db.models.signals import pre_save, post_save


### Helpers ###
re_sig = re.compile(r"^(\w+)/(\w+)/([^/]+)$")

def model_sig(instance):
    cls = instance.__class__
    name = cls._meta.module_name  # activity
    app = cls._meta.app_label     # loft
    pk = instance._get_pk_val()   # 7
    return "%s/%s/%s" % (app, name, pk)

def get_instance_from_sig(path):
    if (':' in path):
        path = path.split(':', 1)[0]
    m = re_sig.match(path)
    if m:
        app, model, pk = m.groups()
        cls = get_model(app, model)
        if cls is None:
            return None
        return cls.objects.get(pk=pk)
    return None


### Signals ###
# These signals are sent on various user operations.
# Subscribers are expected to Raise PermissionDenied if the operation is not allowed.

# Manipulations
# Sent when a user manipulates an object
#   sender:  object being manipulated
#   request: the request used to manipulate the object
#   action:  a slug specifying how it's being manipulated
comment_manipulate = Signal(['request', 'action'])
attachment_manipulate = Signal(['request', 'action'])
document_manipulate = Signal(['request', 'action'])

# View signals
# Sent when a user views an object.
#   sender:  object being viewed
#   request: the request used to view the object
#   context: a context sent to the template renderer
#   - Set context['editable'] to True to make the object editable.
#   - Set context['hidden'] to True to hide the object from view.
library_view = Signal(['request', 'context'])
attachment_view = Signal(['request', 'context'])
document_view = Signal(['request', 'context'])

# Download / View attachment
# Send when a user downloads an attachment.
#   sender: attachment
#   request: the request used to view
attachment_view = Signal(['request'])

# Voting on Comments
#   sender: comment being voted on
#   request: wsgi request
#   vote: the vote object
comment_vote = Signal(['request', 'vote'])

# Event signal
# Sent when an event is created
#   sender:   event object
#   object:   the object being acted on by the event or None if not applicable
#   notify:   set of user objects to notify of the event
#   streams:  set of stream objects to gain the event
#   **kwargs: context used for rendering event templates / emails
#     Receivers are encouraged to alter notify and streams to change who recieves a 
#     notification.  Also if they return a dict, the rendering context will be updated
#     so they can alter how templates are rendered.
event = Signal(['object', 'notify', 'streams'])


### Models ###
class Comment(models.Model):
    path = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    parent = models.ForeignKey("Comment", related_name="children", blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    deleted = models.DateTimeField(blank=True, null=True)
    edited = models.DateTimeField(blank=True, null=True)
    value = models.IntegerField(default=0)

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
        comment_manipulate.send(sender=self, request=request, action='edit')
        self.save()
        return self

    def delete_by_request(self, request):
        self.deleted = datetime.now()
        comment_manipulate.send(sender=self, request=request, action='delete')
        self.save()
        return self

    class Meta:
        ordering = ('path', '-value', 'id')

    @classmethod
    def create_by_request(cls, request, path, body):
        path = path.rstrip('/')
        parent_pk = request.POST.get('parent')
        comment = cls(path=path, body=body, author=request.user)
        if parent_pk:
            comment.parent = Comment.objects.get(pk=parent_pk)
        comment_manipulate.send(sender=comment, request=request, action='create')
        comment.value = 1
        comment.up = True
        comment.save()
        comment.votes.create(user=request.user, value=1)
        return comment

    @property
    def url(self):
        return reverse("discourse:thread", args=[self.path])
    
    @classmethod
    def get_thread(cls, path, user):
        """
        Returns a QuerySet of the media in the given ``path``.
        """
        comments = cls._default_manager.filter(path=path, deleted__isnull=True)
        votes = CommentVote.objects.filter(comment__path=path, 
                                           comment__deleted__isnull=True,
                                           user=user).values_list('comment_id', 'value')
        votes = dict(votes)
        map = {"root": []}
        for comment in comments:
            value = votes.get(comment.id, 0)
            if (value > 0):
                comment.up = True
            if (value < 0):
                comment.down = True
            comment.thread = map.setdefault(comment.id, [])
            print comment.parent_id or "root"
            map.setdefault(comment.parent_id or "root", []).append(comment)
        return map["root"]


def on_comment_save(sender, instance, **kwargs):
    if instance.id is not None:
        instance.value = (
            CommentVote.objects.filter(comment=instance).aggregate(models.Sum('value'))['value__sum'] or 0 )
pre_save.connect(on_comment_save, sender=Comment)


class CommentVote(models.Model):
    comment = models.ForeignKey(Comment, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="comment_votes")
    value = models.IntegerField()

    def __unicode__(self):
        if self.value > 0:
            return "Upvote by %s" % self.user
        elif self.value < 0:
            return "Downvote by %s" % self.user
        else:
            return "Sidevote by %s" % self.user


class Subscription(models.Model):
    path = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    toggle = models.BooleanField(default=True)

    def __unicode__(self):
        return "Subscription(%r, %r, toggle=%r)" % (self.user, self.path, self.toggle)


class Event(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="events_generated")
    type = models.SlugField()
    path = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    def add_to_stream(self, path):
        if isinstance(path, models.Model):
            path = model_sig(path)
        stream, _ = Stream.objects.get_or_create(path=path)
        stream.events.add(self)

    def render(self, request):
        context = RequestContext(request, {'path': self.path, 'event': self})
        return render_to_string(self.template, context)

    def __unicode__(self):
        return "Event(%r, %r, %r)" % (self.actor, self.type, self.path)

    @property
    def object(self):
        if not hasattr(self, '_object'):
            self._object = get_instance_from_sig(self.path)
        return self._object

    @property
    def template(self):
        return "discourse/stream/%s.html" % self.type

    @property
    def url(self):
        if self.object:
            return self.object.url


class Notice(models.Model):
    """
    A notice, shown given to the user when events happen like friending or someone
    responding to a comment on a subscribed path.
    """
    events = models.ManyToManyField(Event)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="notices")
    read = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return "Notice(%s)" % self.id


class Stream(models.Model):
    path = models.CharField(max_length=255)
    events = models.ManyToManyField(Event, related_name="streams")

    def __unicode__(self):
        return "Stream(%s)" % self.path

    def render_events(self, request, size=10, after=None):
        """
        Generates a sequence of events for the stream as simple dicts.

        TODO: Cache this.
        """
        events = self.events.all().order_by('-id')
        if after:
            events = events.filter(id__gt=after)
        events = events[:size]

        context = RequestContext(request, {'stream': self})

        for e in events:
            yield e.render(request)


class Attachment(models.Model):
    path = models.CharField(max_length=255)         # Too small?  Probably.
    mimetype = models.CharField(max_length=255)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    caption = models.TextField(blank=True)
    featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0)
    file = models.FileField(upload_to="attachments")

    def is_an_image(self):
        return "image/" in self.mimetype

    @property
    def url(self):
        return "/discourse/attachments/%s" % (self.path)

    @property
    def filename(self):
        return posixpath.basename(self.path)

    @property
    def icon(self):
        """
        Returns the icon type for the file.
        """
        if "application/pdf" in self.mimetype:
            return "pdf"
        elif "image/" in self.mimetype:
            return "image"
        elif "application/msword" in self.mimetype:
            return "doc"
        elif "officedocument" in self.mimetype:
            return "doc"
        elif self.path.endswith(".pages"):
            return "doc"
        return "blank"

    def info(self):
        return {
            'id': self.id,
            'path': self.path,
            'content_type': self.mimetype,
            'caption': self.caption,
            'order': self.order,
            'filename': self.filename,
            'url': self.url,
            'icon': self.icon
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



class WikiNode(models.Model):
    """
    A node for a wiki.
    """
    parent = models.ForeignKey("WikiNode", blank=True, null=True, related_name="children")
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    path = models.CharField(blank=True, max_length=255)

    def __unicode__(self):
        return self.path

    def branch(self):
        if self.parent:
            return self.parent.branch() + (self,)
        else:
            return (self,)

    def save(self, *args, **kwargs):
        self.path = "/%s" % ("/".join(x.slug for x in self.branch()))
        super(WikiNode, self).save()

        # If we changed our slug, we have to update our children as well so that their paths
        # are correct.
        for c in self.children.all():
            c.save()



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

    def get_content(self, context=None):
        """
        Returns the content as a tree, see _content_tree()
        """
        if context is None:
            context = Context({})
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
                sections = self._content_tree(right, content_map, context)
                is_empty = all(x['is_empty'] for x in sections)
                parts.append({'title': left, 'sections': sections, 'is_empty': is_empty})
            else:
                body = content_map.get(left, '')
                try:
                    body = Template(body).render(context)
                except:
                    pass
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