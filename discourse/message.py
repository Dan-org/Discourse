import urllib, re, mimetypes, hashlib
from datetime import datetime

from django.db import models
from django.apps import apps
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.template import Context, RequestContext
from django.template.loader import render_to_string, TemplateDoesNotExist
from django.utils.safestring import mark_safe

from uuidfield import UUIDField
from yamlfield.fields import YAMLField
from ajax import to_json, from_json, JsonResponse


try:
    import redis
    redis = redis.Redis(host='localhost', port=6379, db=getattr(settings, 'REDIS_DB', 1))
except ImportError:
    redis = None


def hash(*args):
    hsh = hashlib.new('md5')
    for a in args:
        hsh.update(a)
    return hsh.hexdigest()


class Channel(models.Model):
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    tags = models.TextField(blank=True)
    keys = models.TextField(blank=True)
    publish_keys = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="channels")
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "Channel(%s)" % (self.name or self.id)

    def search(self, type=None, tags=None, author=None, parent=None):
        q = self.messages.all()
        if type:
            if isinstance(type, basestring):
                q = q.filter(type=type)
            else:
                q = q.filter(type__in=type)
        if tags:
            for tag in tags:
                q = q.filter(tags__icontains=tag)
        if author:
            q = q.filter(author=author)
        if parent:
            q = q.filter(parent=parent)
        return q

    def publish(self, type, author, tags=None, content=None, save=False, parent=None, attachments=None):
        if not self.created:
            self.created = datetime.now()
            self.save()

        if not author.is_authenticated():
            author = None

        m = Message(channel=self, type=type, author=author, content=content, tags=None, parent=parent)

        if redis:
            redis.publish("channel:%s" % self.id, to_json( m.simple() ))

        if save:
            m.save()

        if attachments:
            for file in attachments:
                m.attach(file)

        return m

    def upload(self, author, files, tags=None, content=None):
        return self.publish("attachment", author, tags=tags, content=content, attachments=files, save=True)

    def download(self, author, attachment_id):
        attachment = get_object_or_404(Attachment.objects.filter(message__channel=self), uuid=attachment_id)
        self.publish("download", author, content={'attachment': attachment})
        return attachment

    def get_attachments(self, **search_options):
        search_options.setdefault('type', ['attachment', 'attachment:meta'])
        messages = self.search(**search_options).select_related('attachments')
        return library(messages)

    def set_attachment_meta(self, author, attachment_id, **kwargs):
        attachment = get_object_or_404(Attachment.objects.filter(message__channel=self), uuid=attachment_id)
        m = self.publish("attachment:meta", author, parent=attachment.message, content={'meta': kwargs, 'filename': attachment.filename, 'filename_hash': hash(attachment.filename)}, save=True)
        return m

    #def rename_attachment(self, author, attachment_id, new_name):
    #    attachment = get_object_or_404(Attachment.objects.filter(message__channel=self), uuid=attachment_id)
    #    m = self.publish("attachment", author, content={'action': 'rename', 'filename': attachment.filename, 'new_name': new_name, 'filename_hash': hash(attachment.filename)}, save=True)
    #    return m

    def render_to_string(self, context, template='discourse/stream.html', type=None, tags=None):
        messages = self.search(type=type, tags=tags)

        if not isinstance(context, Context):
            context = Context(context)

        parts = []
        for m in messages:
            parts.append( m.render_to_string(context) )

        content = mark_safe("\n".join(parts))
        channel = self

        tags = tags or []
        type = type or []

        with context.push(locals()):
            return render_to_string(template, context)

    @property
    def url(self):
        return reverse('discourse:channel', args=[self.id])



class Message(models.Model):
    uuid = UUIDField(auto=True, primary_key=True)
    type = models.SlugField(max_length=255)
    channel = models.ForeignKey(Channel, related_name="messages")
    order = models.IntegerField(default=0)
    parent = models.ForeignKey("Message", blank=True, null=True, related_name="children")
    #thread = models.ForeignKey("Message", blank=True, null=True, related_name="thread_children")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="messages")
    
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    deleted = models.DateTimeField(blank=True, null=True)

    tags = models.CharField(max_length=255, blank=True, null=True)
    keys = models.CharField(max_length=255, blank=True, null=True)
    content = YAMLField(blank=True, null=True)
    value = models.IntegerField(default=0)

    def __unicode__(self):
        return "Message(%r, %r, %r)" % (self.uuid, self.type, self.channel)

    def simple(self):
        return {
            'uuid': self.uuid,
            'type': self.type,
            'channel': {'id': self.channel.id, 'url': self.channel.url},
            'order': self.order,
            'value': self.value,
            'parent': self.parent_id if self.parent else None,
            'author': self.author_id if self.author else None,
            'created': self.created,
            'modified': self.modified,
            'deleted': self.deleted,
            'tags': [x.strip() for x in self.tags.split(':') if x.strip()] if self.tags else [],
            'keys': [x.strip() for x in self.keys.split(':') if x.strip()] if self.keys else [],
            'content': self.content,
            'attachments': [x.simple() for x in self.attachments.all()],
            'url': self.url,
        }

    def attach(self, file):
        mimetype = getattr(file, 'mimetype', mimetypes.guess_type(file.name)[0])

        return self.attachments.create(
            message=self,
            mimetype=mimetype or 'application/octet-stream',
            filename=file.name,
            source=file
        )

    def render_to_string(self, context=None):
        context = context or {}
        context['message'] = self
        context['replies'] = self.children.filter(type='reply').order_by('created')
        try:
            return render_to_string("discourse/message/%s.html" % self.type, context)
        except TemplateDoesNotExist:
            return ""
    
    def likes(self):
        if not hasattr(self, '_likes'):
            users = set()
            for m in self.children.filter(type__in=['like', 'unlike']).select_related('author'):
                if m.type == 'like':
                    users.add(m.author)
                if m.type == 'unlike':
                    users.discard(m.author)
            self._likes = list(users)
        return self._likes

    @property
    def data(self):
        return self.content or {}

    @property
    def url(self):
        return "%s%s/" % (self.channel.url, self.uuid)

    class Meta:
        ordering = ['parent_id', 'order', '-created']


class Attachment(models.Model):
    uuid = UUIDField(auto=True, primary_key=True)
    message = models.ForeignKey(Message, related_name="attachments")
    mimetype = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    source = models.FileField(upload_to="attachments")

    def __unicode__(self):
        return "Attachment(%s, %s)" % (self.uuid, self.filename)

    def simple(self):
        return {
            'uuid': self.uuid,
            'mimetype': self.mimetype,
            'filename': self.filename,
            'url': self.source.url,
            'message': self.message_id,
            'url': self.url,
            'filename_hash': self.filename_hash,
        }

    @property
    def filename_hash(self):
        return hash(self.filename)

    @property
    def url(self):
        return reverse('discourse:attachment', args=[self.message.channel.id, self.uuid]) + self.filename



def library(messages):
    """
    Play through messages to get the current list of attachments.
    """
    by_name = {}
    meta = {}

    for message in messages:
        if message.type == 'attachment:meta':
            meta.setdefault(message.data['filename'].lower(), {}).update(message.data['meta'])
        else:
            for attachment in message.attachments.all():
                filename = attachment.filename.lower()
                meta.setdefault(filename, {})['deleted'] = False
                by_name.setdefault(filename, []).append(attachment)

    attachments = []
    for key in sorted(by_name):
        versions = by_name[key]
        latest = versions[-1]
        latest.versions = versions
        latest.version_number = len(versions)
        latest.__dict__.update(meta.get(key, {}))
        if latest.deleted:
            continue
        attachments.append( latest )

    return attachments


def channel_for(obj):
    if isinstance(obj, Channel):
        id = obj.id
    elif isinstance(obj, basestring):
        id = obj
    elif hasattr(obj, 'get_channel'):
        id = obj.get_channel()
    elif hasattr(obj, 'channel'):
        id = obj.channel
    elif isinstance(obj, models.Model):
        cls = obj.__class__
        app = cls._meta.app_label      # auth
        model = cls._meta.model_name   # User
        pk = str( obj._get_pk_val() )    # 7
        id = "~%s/%s/%s" % ( urllib.quote(app), urllib.quote(model), urllib.quote(pk) )
    else:
        raise TypeError("first argument to channel_for() must be a string or django model")

    return Channel(id=id)


re_model_uri = re.compile(r"\~([^/]+)/([^/]+)/([^/]+)(/.*)?")         # i.e. /<app>/<model>/<pk> [/<rest>]

def object_of_channel(name):
    m = re_model_uri.match(uri)
    if m is None:
        return None, uri
    app, model, pk, rest = m.groups()
    cls = apps.get_model( urllib.unquote(app), urllib.unquote(model) )
    obj = cls.objects.get(pk=urllib.unquote(pk))
    if rest is None:
        return obj, None
    else:
        return obj, urllib.unquote(rest[1:])


from django.shortcuts import render


def channel_view(request, id):
    print "METHOD", request.method
    print "GET", request.GET
    print "POST", request.POST
    print "FILES", request.FILES

    channel = channel_for(id)

    if request.FILES:
        message = channel.upload(request.user, request.FILES.getlist('attachment'))
        return JsonResponse( message.simple() )

    if request.method == 'POST':
        type = request.POST['type']
        tags = [x.strip() for x in request.POST.get('tags', '').split() if x.strip()] or None
        content = request.POST.get('content', None)
        if content:
            content = from_json( content )
        else:
            content = {}

        for k, v in request.POST.items():
            if k.startswith('data-'):
                content[k[5:]] = v

        parent = request.POST.get('parent', None)
        if parent:
            parent = get_object_or_404(Message, pk=parent)
        else:
            parent = None
        message = channel.publish(type, request.user, tags=tags, content=content, parent=parent, save=True)
        simple = message.simple()
        simple['html'] = message.render_to_string(RequestContext(request, locals()))
        return JsonResponse( simple )

    type = [x.strip() for x in request.GET.get('type', '').split(',') if x.strip()] or None
    tags = [x.strip() for x in request.GET.get('tags', '').split(',') if x.strip()] or None
    template = request.GET.get('template', None)

    return HttpResponse( channel.render_to_string(RequestContext(request, locals()), type=type, tags=tags, template=template) )


def attachment(request, channel, attachment):
    channel = channel_for(channel)

    if (request.method == 'POST' and request.POST.get('delete')) or request.method == 'DELETE':
        message = channel.set_attachment_meta(request.user, attachment, deleted=True)
        return JsonResponse( message.simple() )

    if (request.method == 'POST' and 'hidden' in request.POST):
        hidden = request.POST.get('hidden') in ('true', 'True', 'yes', '1')
        message = channel.set_attachment_meta(request.user, attachment, hidden=hidden)
        return JsonResponse( message.simple() )

        message = channel.set_attachment_meta(request.user, attachment, hidden=(request.POST.get('hidden') == 'true'))

    attachment = channel.download(request.user, attachment)

    #if attachment.content_type == 'text/url':
    #    return HttpResponseRedirect(attachment.link)

    return HttpResponseRedirect(attachment.source.url)


    #action = request.GET.get('action');
    #if not action:
    #    return HttpResponseBadRequest("Need an action.")
    return render(request, "discourse/channel.html", locals())