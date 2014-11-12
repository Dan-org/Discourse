from datetime import datetime

from django.db import models
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils.html import normalize_newlines, urlize
from django.core.urlresolvers import reverse

from event import publish, on
from ajax import JsonResponse
from vote import Vote
from uri import *


### Models ###
class Comment(models.Model):
    anchor_uri = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    parent = models.ForeignKey("Comment", related_name="children", blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    deleted = models.DateTimeField(blank=True, null=True)
    edited = models.DateTimeField(blank=True, null=True)
    value = models.IntegerField(default=1)

    class Meta:
        ordering = ('anchor_uri', '-value', 'id')
        app_label = 'discourse'

    def __repr__(self):
        return "Comment(%r, %s)" % (self.anchor_uri, self.id)

    def __unicode__(self):
        return repr(self)

    def info(self):
        return {
            'id': self.id,
            'uri': self.uri,
            'anchor': self.anchor_uri,
            'body': self.body,
            'html': self.html,
            'created': tuple(self.created.timetuple()) if self.created else None,
            'naturaltime': naturaltime(self.created) if self.created else None,
            'deleted': tuple(self.deleted.timetuple()) if self.deleted else None,
            'edited': tuple(self.edited.timetuple()) if self.edited else None,
            'parent': self.parent_id,
            'value': self.value,
            'up': getattr(self, 'up', None),
            'down': getattr(self, 'down', None),
            'author': simple(self.author) if self.author else {
                'name': 'deleted',
                'url': '#'
            }
        }

    @property
    def uri(self):
        return uri(self)

    @property
    def anchor(self):
        if not hasattr(self, '_anchor'):
            self._anchor, self._anchor_extra = resolve_model_uri(self.anchor_uri)
        return self._anchor

    @property
    def html(self):
        return render_to_string("discourse/thread-comment-body.html", {'comment': self})

    def all_children_are_deleted(self):
        for child in self.children.all():
            if not child.deleted:
                return False
            if not child.all_children_are_deleted():
                return False
        return True

    def fix_value(self):
        self.value = Vote.value_for(self)

    def vote(self, user, value):
        Vote.cast(user, self, value)
        self.fix_value()

    @classmethod
    def fix_all_values(cls):
        for comment in cls.objects.all():
            comment.fix_value()
            comment.save()

    @property
    def url(self):
        return reverse("discourse:thread", args=[self.anchor_uri])
    
    @classmethod
    def get_thread(cls, anchor_uri, user):
        """
        Returns a tree of comments.
        """
        comments = cls._default_manager.filter(anchor_uri=anchor_uri)

        map = {"root": []}
        for comment in comments:
            value = Vote.value_for(comment, user=user)      # TODO: Cache this
            if (value > 0):
                comment.up = True
            if (value < 0):
                comment.down = True
            comment.thread = map.setdefault(comment.id, [])
            map.setdefault(comment.parent_id or "root", []).append(comment)
        return map["root"]


### Hooks ###
def on_comment_save(sender, instance, **kwargs):
    if instance.id is not None:
        instance.fix_value()
models.signals.pre_save.connect(on_comment_save, sender=Comment)


@on("vote")
def on_vote(event):
    if isinstance(event.anchor, Comment):
        comment = event.anchor
        comment.fix_value()
        comment.save()
        publish(comment, event.actor, 'comment-vote', data={'value': comment.value})


### Template Tags ###
import ttag

class ThreadTag(ttag.Tag):
    """
    Creates a thread of comments.  

    Usage:
    Create a list of comments anchored on the string "pandas":
        
        {% thread "pandas" %}

    Create a list of comments for a model instance which maps to the string 
    <instance.__class__.__name__.lower()>-<instance private key>, e.g. "post-2".

        {% thread instance %}

    Also, add up and down voting.
        {% thread instance scored=True %}

    See ``discourse/models.py`` on options to change how comments are rendered.
    """
    anchor = ttag.Arg(required=False)                                   # Object or string to anchor to.
    sub = ttag.Arg(default=None, keyword=True, required=False)          # The sub-anchor
    depth = ttag.Arg(default=2, keyword=True)                           # Depth of the comments.
    scored = ttag.Arg(default=False, keyword=True)                      # Whether or not to score the comments.
    template = ttag.Arg(default=None, keyword=True, required=False)     # The template to use for rendering the comments.

    def render(self, context):
        data = self.resolve(context)
        anchor = uri(data.get('anchor'), data.get('sub', None))
        scored = (data.get('scored') == True)
        comments = Comment.get_thread(anchor, context.get('request').user)
        template = data.get('template') or 'discourse/thread.html'

        return render_to_string(template, {'comments': comments, 
                                           'anchor': anchor,
                                           'something': 2,
                                           'depth': data.get('depth'),
                                           'scored': scored,
                                           'auth_login': settings.LOGIN_REDIRECT_URL}, context)
    class Meta:
        name = "thread"


class ThreadCountTag(ttag.Tag):
    """
    Returns the count of comments.
    """
    anchor = ttag.Arg(required=False)                                   # Object or string to anchor to.
    sub = ttag.Arg(default=None, keyword=True, required=False)          # The sub-thread
    parent = ttag.Arg(default=None, keyword=True, required=False)       # Only count comments below this one

    def render(self, context):
        data = self.resolve(context)
        anchor = uri(data.get('anchor'), data.get('sub', None))
        parent = data.get('parent')
        scored = bool( data.get('scored') )
        if parent:
            count = Comment.objects.filter(anchor_uri=anchor, deleted__isnull=True, parent=parent).count()
        else:
            count = Comment.objects.filter(anchor_uri=anchor, deleted__isnull=True).count()
        if count == 0:
            return ""
        elif count == 1:
            return "1 Comment"
        else:
            return "%d Comments" % count

    class Meta:
        name = "threadcount"


### Helpers ###
def create_comment(request, uri):
    body = request.POST['body']
    parent_pk = request.POST.get('parent')
    parent = Comment.objects.get(pk=parent_pk) if parent_pk else None

    if not publish(uri, request.user, 'comment', data={'body': body, 'parent': parent}, record=True):
        raise PermissionDenied()

    comment = Comment.objects.create(
                anchor_uri=uri, 
                body=body, 
                author=request.user,
                parent_id=parent_pk or None
    )
    comment.vote(request.user, 1)           # The user starts with themselves upvoting their comment.
    comment.up = True

    publish(uri, request.user, 'create', comment)
    
    return comment


def edit_comment(request, comment):
    body = request.POST['body']
    if not publish(comment, request.user, 'edit', data={'body': body}, record=True):
        raise PermissionDenied()
    comment.body = body
    comment.edited = datetime.now()
    comment.save()
    return comment


def delete_comment(request, comment):
    if not publish(comment, request.user, 'delete', record=True):
        raise PermissionDenied()
    
    comment.deleted = datetime.now()

    if comment.children.count() > 0 and not comment.all_children_are_deleted():
        comment.save()
    else:
        comment.delete()


### Views ###
@login_required
def manipulate(request, uri):
    """
    Brantley Harris: Comment manipulation #yodawg
    two days ago - [delete] [edit] [like]
    """
    if not request.POST:
        return HttpResponseBadRequest()

    pk = request.POST.get('id')
    delete = request.POST.get('delete', '').lower()

    if pk:
        comment = get_object_or_404(Comment, pk=pk, anchor_uri=uri)
        if delete in ('yes', 'true'):
            delete_comment(request, comment)
        else:
            edit_comment(request, comment)
    else:
        comment = create_comment(request, uri)

    if request.is_ajax():
        data = comment.info()
        data['editable'] = True
        return JsonResponse(data)
    else:
        next = request.POST.get('next', None)
        return HttpResponseRedirect("%s#discourse-comment-%s" % (next, comment.id))

    scored = False
    depth = 1
    comments = Comment.get_thread(path, request.user)
    template = request.GET.get('template') or 'discourse/thread.html'

    html = render_to_string(template, {'comments': comments,
                                       'path': path,
                                       'depth': depth,
                                       'scored': scored,
                                       'auth_login': settings.LOGIN_REDIRECT_URL})
    
    return HttpResponse(json.dumps({'html': html}), content_type="application/json")

