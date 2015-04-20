import urllib, re, mimetypes, hashlib, time, numbers, inspect
from django.utils import timezone
from pprint import pprint
from datetime import datetime
from uuid import uuid4

from django.db import models
from django.apps import apps
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.template import Context, RequestContext
from django.template.loader import render_to_string, TemplateDoesNotExist
from django.utils.safestring import mark_safe
from django.dispatch import Signal
from django.contrib.auth import get_user_model

from haystack.query import SearchQuerySet
from haystack.models import SearchResult

from uuidfield import UUIDField
from yamlfield.fields import YAMLField
from ajax import to_json, from_json, JsonResponse

from uri import uri, resolve_model_uri


event_signal = Signal(['event'])


try:
    import redis
    redis = redis.Redis(host='localhost', port=6379, db=getattr(settings, 'REDIS_DB', 1))
except ImportError:
    redis = None


def to_datetime(dt, or_now=False):
    if isinstance(dt, tuple) or isinstance(dt, list):
        time_tuple = time.struct_time(dt)
        return datetime.fromtimestamp(time.maketime(time_tuple))
    elif isinstance(dt, numbers.Real):
        return timezone.make_aware( datetime.fromtimestamp(dt), timezone.get_current_timezone() )
    if not dt and or_now:
        return timezone.now()
    return dt


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

    def simple(self):
        return {
            'id': self.id,
            'name': self.name,
            'created': self.created,
            'url': self.url,
        }

    def search(self, type=None, tags=None, author=None, parent=None):
        q = SearchQuerySet().models(Message).result_class(MessageResult) # self.messages.all() # 

        q = q.filter(channel__exact=self.id)

        if type:
            if isinstance(type, basestring):
                q = q.filter(type=type)
            else:
                q = q.filter(type__in=type)
        if tags:
            q = q.filter(tags__in=tags)
        if author:
            q = q.filter(author=author)
        if parent:
            q = q.filter(parent=parent)

        return q
    
    def publish(self, type, author, tags=None, data=None, save=False, parent=None, attachments=None):
        # If the channel hasn't been saved, now we save it.
        if not self.created and save:
            self.created = timezone.now()
            self.save()

        # If the author is anonymous, we make it None
        if not author.is_authenticated():
            author = None

        # Generate the uuid, if necessary
        if save:
            uuid = uuid4().hex
        else:
            uuid = None

        print "PUBLISH", type, author

        # Create message, give it its initial data.
        message = MessageType(type=type, uuid=uuid)
        message.unpack({
            'channel': self,
            'author': author,
            'parent': parent,
            'data': data,
            'tags': tags,
        })

        # Allow message to build itself / initialize anything necessary.
        message.build()

        # Add attachments
        message._attachments = attachments

        # Signal to all hooked functions
        if not message.signal():
            logger.info("EVENT CANCELED:\n%r", m)
            return None

        # Broadcast to redis or what have you
        message.broadcast()

        # Save if requested
        if save:
            message.save(create=True, update_relations=True)

        return message

    def upload(self, author, files, tags=None, data=None):
        return self.publish("attachment", author, tags=tags, data=data, attachments=files, save=True)

    def download(self, author, attachment_id):
        attachment = get_object_or_404(Attachment.objects.filter(message__channel=self), uuid=attachment_id)
        self.publish("download", author, data={'attachment': attachment})
        return attachment

    def get_attachments(self, **search_options):
        search_options.setdefault('type', ['attachment', 'attachment:meta'])
        messages = [m for m in self.search(**search_options)]
        return library(messages)

    def set_attachment_meta(self, author, attachment_id, **kwargs):
        attachment = get_object_or_404(Attachment.objects.filter(message__channel=self), uuid=attachment_id)
        m = self.publish("attachment:meta", author, parent=attachment.message, data={'meta': kwargs, 'filename': attachment.filename, 'filename_hash': hash(attachment.filename)}, save=True)
        return m

    #def rename_attachment(self, author, attachment_id, new_name):
    #    attachment = get_object_or_404(Attachment.objects.filter(message__channel=self), uuid=attachment_id)
    #    m = self.publish("attachment", author, content={'action': 'rename', 'filename': attachment.filename, 'new_name': new_name, 'filename_hash': hash(attachment.filename)}, save=True)
    #    return m

    def render_to_string(self, context, template='discourse/stream.html', type=None, tags=None, sort=None):
        messages = self.search(type=type, tags=tags)

        if sort == 'recent':
            messages = messages.order_by('-created')
        elif sort == 'value':
            messages = messages.order_by('-value', '-created')

        if not isinstance(context, Context):
            context = Context(context)

        parts = []
        for m in messages:
            try:
                parts.append( m.render(context) )
            except TemplateDoesNotExist:
                continue

        content = mark_safe("\n".join(parts))
        channel = self

        tags = tags or []
        type = type or []

        with context.push(locals()):
            return render_to_string(template, context)

    @property
    def url(self):
        return reverse('discourse:channel', args=[self.id])


def attach(message, file):
    mimetype = getattr(file, 'mimetype', mimetypes.guess_type(file.name)[0])

    return Attachment.objects.create(
        message_uuid = message['uuid'],
        mimetype = mimetype or 'application/octet-stream',
        filename = file.name,
        source = file
    )


def render_message(message, context):
    if not isinstance(message, dict):
        message = message.simple()

    if 'html' in message:
        return message['html']

    context = context or {}
    context.push({
        'message': message,
        'replies': message['data'].get('replies', []),
    })
    try:
        if '_template' in message:
            return render_to_string(message['_template'], context)
        return render_to_string("discourse/message/%s.html" % message['type'], context)
    except TemplateDoesNotExist:
        return ""



class Message(models.Model):
    uuid = UUIDField(auto=False, primary_key=True)
    type = models.SlugField(max_length=255)
    channel = models.ForeignKey(Channel, related_name="messages")
    order = models.IntegerField(default=0)
    depth = models.IntegerField(default=0)
    parent = models.ForeignKey("Message", blank=True, null=True, related_name="children")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="messages")
    
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    deleted = models.DateTimeField(blank=True, null=True)

    tags = models.TextField(blank=True, null=True)
    keys = models.TextField(blank=True, null=True)
    content = YAMLField(blank=True, null=True)
    value = models.IntegerField(default=0)

    def __unicode__(self):
        return "Message('%s', type='%s', channel='%s')" % (self.uuid, self.type, self.channel.id)

    def rebuild(self):
        if not hasattr(self, '_message'):
            self._message = MessageType(self.type, self.uuid.hex)
            dct = {
                'uuid': self.uuid.hex if self.uuid else None,
                'type': self.type,
                'channel': self.channel,
                'order': self.order,
                'parent': self.parent_id,
                'depth': self.depth,
                'author': self.author,
                'created': self.created,
                'modified': self.modified,
                'deleted': self.deleted,
                'tags': [x.strip() for x in self.tags.split(' ') if x.strip()] if self.tags else (),
                'keys': [x.strip() for x in self.keys.split(' ') if x.strip()] if self.keys else (),
                'data': self.content,
                'attachments': [x.simple() for x in self.attachments.all()],
                'url': self.url
            }
            self._message.unpack(dct)
        return self._message

    @property
    def url(self):
        return "%s%s/" % (self.channel.url, self.uuid)

    class Meta:
        ordering = ['depth', 'parent_id', 'order', '-created']


#def render_to_string(self, context=None):
#    context = context or {}
#    if hasattr(self, 'state'):
#        context['message'] = self.state
#        context['replies'] = self.state['data'].get('replies', [])
#    else:
#        context['message'] = getattr(self, 'state', self)
#        context['replies'] = self.children.all()
#    try:
#        return render_to_string("discourse/message/%s.html" % self.type, context)
#    except TemplateDoesNotExist:
#        return ""

class MessageMeta(type):
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, '_registry'):
            # this is the base class.  Create an empty registry
            cls._registry = {}
        else:
            # this is a derived class.  Add cls to the registry
            name = dct.get('type', name.lower())
            cls._registry[name] = cls
        
        super(MessageMeta, cls).__init__(name, bases, dct)


class MessageType(object):
    __metaclass__ = MessageMeta

    def __init__(self, type, uuid=None):
        self.uuid = uuid
        self.type = type
        self.html = None
        if self.type in self._registry:
            self.__class__ = self._registry[self.type]

    def post(self, request):
        try:
            self.html = self.render(RequestContext(request, {}))
        except TemplateDoesNotExist:
            pass
        return JsonResponse( self.pack() )

    def inform(self, request):
        try:
            self.html = self.render(RequestContext(request, {}))
        except TemplateDoesNotExist:
            pass
        return self.pack()

    def render(self, context):
        context.push({'message': self})
        return render_to_string(["discourse/message/%s.html" % self.type], context)

    def describe(self):
        pass

    def pack(self):
        simple = {
            'type': self.type,
            'uuid': self.uuid,

            'channel': self.channel,
            'author': self.author,
            'parent': self.parent,

            'created': self.created,
            'modified': self.modified,

            'url': self.url,
        }

        if self.order: simple['order'] = self.order
        if self.value: simple['value'] = self.value
        if self.deleted: simple['deleted'] = self.deleted
        if self.keys: simple['keys'] = list(self.keys)
        if self.tags: simple['tags'] = list(self.tags)
        if self.attachments: simple['attachments'] = list(self.attachments)
        if self.html: simple['html'] = self.html

        if self.data:
            if 'children' in self.data:
                simple['data'] = dict(self.data)
                simple['data']['children'] = [c.pack() for c in self.data['children']]
            else:
                simple['data'] = self.data

        return simple

    def unpack(self, state):
        # Get channel
        self.channel = state['channel']
        if isinstance( self.channel, models.Model ):
            self.channel, self._channel = self.channel.id, self.channel

        # Get author
        self.author = state['author']
        if isinstance( self.author, basestring ):
            self.author = from_json(self.author)
        elif isinstance( self.author, models.Model ):
            self.author, self._author = self.author.simple(), self.author
        
        # Get parent
        self.parent = state.get('parent', None)
        if isinstance( self.parent, models.Model ):
            self.parent = self.parent.uuid
        if isinstance( self.parent, MessageType ):
            self.parent, self._parent = self.parent.uuid, self.parent

        self.order = state.get('order', 0)
        self.value = state.get('order', 0)

        self.created = to_datetime(state.get('created'), or_now=True)
        self.modified = to_datetime(state.get('modified'), or_now=True)
        self.deleted = to_datetime(state.get('deleted', None))

        self.keys = set(state.get('keys') or ())
        self.tags = set(state.get('tags') or ())

        attachments = state.get('attachments') or []
        if isinstance(attachments, basestring):
            self.attachments = from_json(attachments)
        else:
            self.attachments = attachments

        data = state.get('data') or {}
        if isinstance(data, basestring):
            self.data = from_json(data)
        else:
            self.data = data

        if 'children' in self.data:
            self.data['children'] = [MessageType.rebuild(x) for x in self.data['children']]

    def build(self):
        pass

    def apply(self, parent):
        pass

    def attach(self, file):
        mimetype = getattr(file, 'mimetype', mimetypes.guess_type(file.name)[0])

        a = Attachment.objects.create(
            message = self.get_record(),
            mimetype = mimetype or 'application/octet-stream',
            filename = file.name,
            source = file
        )

        self.attachments.append(a.simple())

    def cap(self, parent, children):
        pass

    def save(self, create=False, update_relations=False):
        if create:
            record = Message(uuid=self.uuid)
        else:
            try:
                record = Message.objects.get(uuid=self.uuid)
            except Message.DoesNotExist:
                record = Message()

        record.type = self.type
        record.created = self.created
        record.modified = self.modified
        record.deleted = self.deleted
        record.order = self.order
        
        record.keys = " ".join(self.keys)
        record.tags = " ".join(self.tags)
        record.content = self.data

        if update_relations:
            record.channel = self.get_channel()
            record.parent = self.get_parent_record()
            record.author = self.get_author()

            if record.parent:
                record.depth = record.parent.depth + 1

        # Save
        record.save()

        # Save our record
        record._message = self
        self._record = record

        # Resolve attachments
        if hasattr(self, '_attachments') and self._attachments:
            for file in self._attachments:
                self.attach(file)

        return record

    def broadcast(self):
        print "BROADCAST", self.channel, self.type
        if redis:
            redis.publish(self.channel, to_json( self.pack() ))

    def signal(self):
        for reciever, result in event_signal.send(sender=None, message=self):
            if result is False:
                logger.info("EVENT CANCELED:\n%r", self)
                return False
        return True

    def get_channel(self):
        if not hasattr(self, '_channel'):
            self._channel = Channel.objects.get(id=self.channel)
        return self._channel

    def get_parent(self):
        if not self.parent:
            return None

        if not hasattr(self, '_parent'):
            self._parent = SearchQuerySet().models(Message).result_class(MessageResult).filter(uuid=self.parent)[0]

        return self._parent

    def get_parent_record(self):
        if not self.parent:
            return None

        if hasattr(self, '_parent'):
            return self._parent.get_record()
            
        if not hasattr(self, '_parent_record'):
            self._parent_record = Message.objects.get(uuid=self.parent)
        return self._parent_record

    def get_children(self):
        return SearchQuerySet().models(Message).result_class(MessageResult).filter(parent=self.uuid)

    def get_author(self):
        if not hasattr(self, '_author'):
            self._author = get_user_model().objects.get(pk=self.author['id'])
        return self._author

    def get_record(self):
        if not hasattr(self, '_record'):
            self._record = Message.objects.get(uuid=self.uuid)
        return self._record

    @property
    def url(self):
        url = reverse( "discourse:channel", args=[self.channel] )
        #if self.uuid:
        #    return "{}{}/".format(url, self.uuid)
        return url

    @classmethod
    def hook(cls, fn):
        hook(cls.type, fn)

    @classmethod
    def rebuild(self, state, **extra):
        if isinstance(state, MessageType):
            return state
        message = MessageType(type=state['type'], uuid=state['uuid'])
        message.unpack(state)
        message.__dict__.update(extra)
        return message


def MessageResult(app_label, model_name, pk, score, **kwargs):
    result = {
        'app_label': app_label,  
        'model_name': model_name,  
        'pk': pk,  
        'score': score,
    }
    return MessageType.rebuild(kwargs, result=result)



#class MessageResult(SearchResult):
#    def __init__(self, app_label, model_name, pk, score, **kwargs):
#        super(MessageResult, self).__init__(app_label, model_name, pk, score, **kwargs)
#        self.author = from_json(self.author)
#        self.data = from_json(self.data) if self.data else {}
#        for 
#
#    def __repr__(self):
#        return "%s(%s)" % (self.__class__.__name__, self.pk)
#
#    def unpack(self, data):
#        data['created'] = datetime(*data['created'][:6])
#        return data
#
#    def render_to_string(self, context=None):
#        context = context or {}
#        context['message'] = self.__dict__
#        context['replies'] = [self.unpack(x) for x in self.data.get('replies', [])]
#        try:
#            return render_to_string("discourse/message/%s.html" % self.type, context)
#        except TemplateDoesNotExist:
#            return ""
#
#    def simple(self):
#        simple = self.get_additional_fields()
#        simple['_result'] = {
#            'app_label': self.app_label,
#            'model_name': self.model_name,
#            'pk': self.pk,
#            'score': self.score
#        }
#        return simple



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
            for attachment in message.get_record().attachments.all():
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


def on(*types):
    def decorator(fn):
        hook(fn, *types)
        return fn
    return decorator


def hook(fn, *types):
    if settings.DEBUG:
        filename = inspect.getsourcefile(fn)
        filename = filename[filename.find('loft/') + 5:]
        source, lineno = inspect.getsourcelines(fn)
        print "HOOK {} - {}:{}".format(" ".join(types), filename, lineno)

    def subscription(sender, message, **kwargs):
        if '*' in types or message.type in types:
            return fn(message)
    event_signal.connect(subscription, weak=False)


def channel_for(obj):
    if isinstance(obj, Channel):
        return obj
    elif isinstance(obj, basestring):
        id = obj
    elif hasattr(obj, 'get_channel'):
        id = obj.get_channel()
    elif hasattr(obj, 'channel'):
        id = obj.channel
    elif isinstance(obj, models.Model):
        id = uri(obj)
    elif isinstance(obj, type) and issubclass(obj, models.Model):
        id = uri(obj)
    else:
        raise TypeError("first argument to channel_for() must be a string or django model, not whatever this is: %r" % obj)

    return Channel(id=id)





def channel_view(request, id, message_id=None):
    print "METHOD", request.method
    print "GET", request.GET
    print "POST", request.POST
    print "FILES", request.FILES

    channel = channel_for(id)

    if request.FILES:
        message = channel.upload(request.user, request.FILES.getlist('attachment'))
        return message.post(request)

    if request.method == 'POST':
        if not request.user.is_authenticated():
            raise Http404

        type = request.POST['type']
        tags = [x.strip() for x in request.POST.getlist('tags', []) if x.strip()] or None
        data = request.POST.get('data', None)
        if data:
            data = from_json( data )
        else:
            data = {}

        for k, v in request.POST.items():
            if k.startswith('data-'):
                data[k[5:]] = v

        parent = request.POST.get('parent', None)
        if parent:
            parent = get_object_or_404(Message, pk=parent)
        else:
            parent = None
        message = channel.publish(type, request.user, tags=tags, data=data, parent=parent, save=True)
        return message.post(request)

    type = expand_tags(request.GET.getlist('type[]'))
    tags = expand_tags(request.GET.getlist('tags[]'))

    sort = request.GET.get('sort', 'recent')
    template = request.GET.get('template', None)

    return HttpResponse( channel.render_to_string(RequestContext(request, locals()), type=type, tags=tags, sort=sort, template=template) )


def expand_tags(tags):
    if not tags:
        return None
    results = []
    for t in tags:
        results.extend( t.split() )
    return filter(None, [x.strip() for x in results]) or None


def attachment(request, channel, attachment):
    channel = channel_for(channel)

    if (request.method == 'POST' and request.POST.get('delete')) or request.method == 'DELETE':
        message = channel.set_attachment_meta(request.user, attachment, deleted=True)
        return JsonResponse( message.pack() )

    if (request.method == 'POST' and 'hidden' in request.POST):
        hidden = request.POST.get('hidden') in ('true', 'True', 'yes', '1')
        message = channel.set_attachment_meta(request.user, attachment, hidden=hidden)
        return JsonResponse( message.pack() )

        message = channel.set_attachment_meta(request.user, attachment, hidden=(request.POST.get('hidden') == 'true'))

    attachment = channel.download(request.user, attachment)

    #if attachment.content_type == 'text/url':
    #    return HttpResponseRedirect(attachment.link)

    return HttpResponseRedirect(attachment.source.url)


    #action = request.GET.get('action');
    #if not action:
    #    return HttpResponseBadRequest("Need an action.")
    return render(request, "discourse/channel.html", locals())


class Like(MessageType):
    def apply(self, parent):
        likes = set( parent.data.get('likes', ()) )
        if self.author['id'] in likes:
            return
        likes.add(self.author['id'])

        parent.data['likes'] = likes
        parent.value += 1

    def post(self, request):
        from discourse.templatetags.discourse import like
        context = RequestContext(request)
        m = self.get_parent()
        
        context.push( like(context, self.get_parent()) )
        try:
            self.html = render_to_string( "discourse/likes.html", context )
        except TemplateDoesNotExist:
            pass

        return JsonResponse(self.pack())


class Unlike(Like):
    def apply(self, other):
        likes = set( other.data.get('likes', ()) )
        if self.author['id'] not in likes:
            return

        likes.remove(self.author['id'])
        other.data['likes'] = likes
        other.value -= 1



class Reply(MessageType):
    def apply(self, parent):
        parent.data.setdefault('children', []).append(self)





#class AttachmentMeta(MessageType):
#    type = "attachment:meta"
#    def apply(self, parent):
#        pass
#        #parent.data.setdefault(self.data['filename'].lower(), {}).update(self.data['meta'])
#        #parent.data.update(self.data)
#
#