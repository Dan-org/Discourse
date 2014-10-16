from django.db import models
from django.conf import settings

from vote import Vote
from uri import uri


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
            'anchor': self.anchor_uri,
            'html': self.render_body(),
            'text': self.body,
            'created': tuple(self.created.timetuple()) if self.created else None,
            'naturaltime': naturaltime(self.created) if self.created else None,
            'deleted': tuple(self.deleted.timetuple()) if self.deleted else None,
            'edited': tuple(self.edited.timetuple()) if self.edited else None,
            'parent': self.parent_id,
            'value': self.value,
            'up': getattr(self, 'up', None),
            'down': getattr(self, 'down', None),
            'author': self.author.simple() if self.author else {
                'name': deleted,
                'url': '#'
            }
        }

    @property
    def anchor(self):
        if not hasattr(self, '_anchor'):
            self._anchor, self._anchor_extra = resolve_model_uri(self.anchor_uri)
        return self._anchor

    def render_body(self):
        return urlize(normalize_newlines(self.body).replace('\n', '<br>'))

    def edit_by_request(self, request, body):
        self.body = body
        self.edited = datetime.now()
        comment_manipulate.send(sender=self, request=request, action='edit')
        self.save()
        return self

    def delete_by_request(self, request):
        comment_manipulate.send(sender=self, request=request, action='delete')
        if self.children.count() > 0 and not self.all_children_are_deleted():
            self.deleted = datetime.now()
            self.save()
        else:
            self.delete()
        return self

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

    @classmethod
    def create_by_request(cls, request, anchor_uri, body):
        anchor_uri = anchor_uri.rstrip('/')
        parent_pk = request.POST.get('parent')
        comment = cls(anchor_uri=anchor_uri, body=body, author=request.user)
        if parent_pk:
            comment.parent = Comment.objects.get(pk=parent_pk)
        comment.value = 1
        comment.up = True
        comment.save()
        comment.votes.create(user=request.user, value=1)
        comment_manipulate.send(sender=comment, request=request, action='create')
        return comment

    @property
    def url(self):
        return reverse("discourse:thread", args=[self.anchor_uri])
    
    @classmethod
    def get_thread(cls, anchor_uri, user):
        """
        Returns a tree of comments.
        """
        comments = cls._default_manager.filter(anchor_uri=anchor_uri)
        if (user.is_authenticated()):
            votes = Vote.value_for(self, uer=user)
            votes = dict(votes)
        else:
            votes = {}

        map = {"root": []}
        for comment in comments:
            value = votes.get(comment.id, 0)
            if (value > 0):
                comment.up = True
            if (value < 0):
                comment.down = True
            comment.thread = map.setdefault(comment.id, [])
            map.setdefault(comment.parent_id or "root", []).append(comment)
        return map["root"]


def on_comment_save(sender, instance, **kwargs):
    if instance.id is not None:
        instance.fix_value()
models.signals.pre_save.connect(on_comment_save, sender=Comment)


