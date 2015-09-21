import gevent
import urllib, re, mimetypes, hashlib, time, numbers, inspect, logging

from pprint import pprint
from datetime import datetime, date
from uuid import uuid4

from django.db import models
from django.apps import apps
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseBadRequest
from django.template import Context, RequestContext
from django.utils.safestring import mark_safe
from django.dispatch import Signal
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date

from haystack.query import SearchQuerySet, SQ
from haystack.models import SearchResult

from uuidfield import UUIDField
from yamlfield.fields import YAMLField
from ajax import to_json, from_json, JsonResponse

from uri import uri, resolve_model_uri, simple
from template import render_to_string, TemplateDoesNotExist


logger = logging.getLogger(__name__)
event_signal = Signal(['event'])


try:
    import redis
    redis = redis.Redis(host='localhost', port=6379, db=getattr(settings, 'REDIS_DB', 1))
except ImportError:
    print "Cannot find redis."
    redis = None


def to_datetime(dt, or_now=False):
    if isinstance(dt, tuple) or isinstance(dt, list):
        time_tuple = time.struct_time(dt)
        return timezone.localtime( datetime.fromtimestamp(time.maketime(time_tuple)) )
    elif isinstance(dt, numbers.Real):
        return timezone.make_aware( datetime.fromtimestamp(dt), timezone.get_current_timezone() )
    elif dt and isinstance(dt, basestring):
        as_datetime = parse_datetime(dt)
        if as_datetime:
            if timezone.is_naive(as_datetime):
                as_datetime = datetime(as_datetime.year, as_datetime.month, as_datetime.day, as_datetime.hour, as_datetime.minute, as_datetime.day, tzinfo=timezone.UTC())
            return timezone.localtime(as_datetime)
    elif isinstance(dt, datetime):
        if timezone.is_naive(dt):
            dt = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.day, tzinfo=timezone.UTC())
        return dt
    elif not dt and or_now:
        return timezone.now()
    return dt


def hash(*args):
    hsh = hashlib.new('md5')
    for a in args:
        if isinstance(a, unicode):
            a = a.encode('ascii', 'ignore')
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

    def search(self, type=None, require_all=None, require_any=None, require_not=None, author=None, parent=None, deleted=False, sort='recent'):
        q = SearchQuerySet().models(Message).result_class(MessageResult)

        q = q.filter(SQ(channel__exact=self.id) | SQ(tags=self.id))

        if require_not:
            if require_any:
                require_not -= require_any
            if require_all:
                require_not -= require_all

        if type:
            if isinstance(type, basestring):
                q = q.filter(type__exact=type)
            else:
                q = q.filter(type__in=type)
        if require_all:
            require_all = set(require_all)
            sq = SQ(tags=require_all.pop())
            while require_all:
                sq = sq & SQ(tags=require_all.pop())
            q = q.filter(sq)
        if require_any:
            q = q.filter(tags__in=require_any)
        if require_not:
            q = q.exclude(tags__in=require_not)
        if author:
            q = q.filter(author=author)
        if parent:
            q = q.filter(parent=parent)

        if not deleted:
            q = q.exclude(status='deleted')

        if sort == 'recent':
            q = q.order_by('-created')
        elif sort == 'value':
            q = q.order_by('-value', '-created')

        return q

    def get_anchor(self):
        if not hasattr(self, '_anchor'):
            self._anchor, _ = resolve_model_uri(self.id)
        return self._anchor

    def get_message(self, uuid):
        return SearchQuerySet().models(Message).result_class(MessageResult).filter(uuid=uuid)[0]
    
    def publish(self, type, author, data=None, tags=None, save=False, parent=None, attachments=None, broadcast=True, jinja=False):
        start = time.time()

        # If the channel hasn't been saved, now we save it.
        if not self.created and save:
            self.created = timezone.now()
            self.save()

        # If the author is anonymous, we make it None
        if author is None or not author.is_authenticated():
            author = None

        # Generate the uuid, if necessary
        if save:
            uuid = uuid4().hex
        else:
            uuid = None

        # Create message, give it its initial data.
        message = MessageType(type=type, uuid=uuid)
        message.unpack({
            'channel': self,
            'author': author,
            'parent': parent,
            'data': data,
            'tags': tags,
        })
        message.saveable = save
        message.jinja = jinja

        if author:
            message.tags.add(uri(author))

        # Add attachments
        if attachments:
            for file in attachments:
                message.attach(file)

        # Allow message to build itself / initialize anything necessary.
        message.build()

        if settings.DEBUG:
            print "New Message:", message.__class__.__name__
            pprint(message.pack())

        # Signal to all hooked functions
        if not message.signal():
            logger.debug("CANCELED - {!r}\n     type={!r}\n     author='{!s}'\n     parent={!r}\n     tags={!r}\n     time={}".format(self.id, type, author, parent, tags, (time.time() - start) * 1000))
            return None

        # Broadcast to redis or what have you
        if broadcast or (broadcast is None and save):
            gevent.spawn_raw(message.broadcast)

        # Save if requested
        if save and message.saveable:
            message.save(create=True, update_relations=True)

        logger.debug("PUBLISH - {!r}\n     type={!r}\n     author='{!s}'\n     parent={!r}\n     tags={!r}\n     time={}".format(self.id, type, author, parent, tags, (time.time() - start) * 1000))
        return message

    def upload(self, author, files, tags=None, data=None):
        return self.publish("attachment", author, tags=tags, data=data, attachments=files, save=True)

    def download(self, author, attachment_id, filename):
        attachment = get_object_or_404(Attachment, message__uuid=attachment_id, filename=filename)
        self.publish("download", author, data={'attachment': attachment})
        return attachment

    def download_by_filename(self, author, filename):
        for msg in self.get_attachments( self.search(type='attachment') ):
            if msg.data['filename'] == filename:
                return HttpResponseRedirect( msg.data['url'] )
        raise Http404

    def get_attachments(self, messages, deleted=False):
        by_filename = {}
        for message in messages:
            if message.type not in ('attachment', 'attachment:link') or (message.deleted and not deleted):
                continue
            elif not isinstance(message.data, dict):
                continue
            elif not 'filename' in message.data:
                continue
            if message.type == 'attachment:link':
                if '://' not in message.data['url']:
                    message.data['url'] = 'http://' + message.data['url']
            by_filename.setdefault(message.data.get('filename_hash'), message)

        return [x for x in by_filename.values() if not x.data.get('deleted')]

    def set_attachment_meta(self, author, attachment_id, **kwargs):
        attachment = get_object_or_404(Attachment.objects.filter(message__channel=self), uuid=attachment_id)
        m = self.publish("attachment:meta", author, parent=attachment.message, data={'meta': kwargs, 'filename': attachment.filename, 'filename_hash': hash(attachment.filename)}, save=True)
        return m

    def render_to_string(self, context, messages, template=None):
        can_edit_channel = context.get('can_edit_channel', None)
        if not can_edit_channel and hasattr(self.get_anchor(), 'can_edit') and 'request' in context:
            can_edit_channel = self.get_anchor().can_edit(context['request'].user)

        context['can_edit_channel'] = can_edit_channel

        template = template or 'discourse/stream.html'
        channel = self
        content = None

        parts = []
        for m in messages:
            try:
                if m.channel == self.id:
                    parts.append( m.render(context, locals()) )
                else:
                    parts.append( m.inform(context, locals()) )
            except TemplateDoesNotExist:
                continue
        content = mark_safe("\n".join(parts))

        return render_to_string(template, context, locals())

    @property
    def url(self):
        return reverse('discourse:channel', args=[self.id])



class Message(models.Model):
    uuid = UUIDField(auto=False, primary_key=True)
    type = models.SlugField(max_length=255)
    channel = models.ForeignKey(Channel, related_name="messages")
    order = models.IntegerField(default=0)
    depth = models.IntegerField(default=0)
    parent = models.ForeignKey("Message", blank=True, null=True, related_name="children")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="messages")
    
    created = models.DateTimeField()
    modified = models.DateTimeField(blank=True, null=True)
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
                'url': self.url,
                'value': self.value,
            }
            self._message.unpack(dct)
            self._message.build()
        return self._message

    @property
    def url(self):
        return "%s%s/" % (self.channel.url, self.uuid)

    class Meta:
        ordering = ['depth', 'parent_id', 'order', '-created']


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
        self.html = None
        self.set_type(type)

    def __repr__(self):
        return "%s('%s', type='%s', channel='%s')" % (self.__class__.__name__, self.uuid, self.type, self.channel)

    def __unicode__(self):
        return repr(self)

    def set_type(self, type):
        self.type = type
        if type in self._registry:
            self.__class__ = self._registry[self.type]
        else:
            self.__class__ = MessageType

    def post(self, request):
        try:
            self.html = self.render({'can_edit_message': True, 'can_edit_channel': True, 'request': request, 'inform': False, 'JINJA': request.META.get('HTTP_X_JINJA') == 'true'})
        except TemplateDoesNotExist:
            pass
        return JsonResponse( self.pack() )

    def inform(self, context, context_update):
        context_update = context_update or {}
        context_update['inform'] = True
        return self.render(context, context_update)

    def describe(self, user):
        return None

    def emit(self, socket, context):
        if not self.save:
            return

        try:
            self.html = self.render(context)
        except TemplateDoesNotExist:
            pass
        return socket.emit('message', self.pack())

    def render(self, context, context_update=None):
        user = context['request'].user
        can_edit_channel = context.get('can_edit_channel', False)
        can_edit_message = context.get('can_edit_message', (user.is_superuser or user.id == self.author.get('id')))
        can_delete_message = context.get('can_edit_message', (can_edit_channel or user.is_superuser or user.id == self.author.get('id')))
        message = self
        data = self.data
        context_update = context_update or {}
        context_update.update(locals())

        return render_to_string(["discourse/message/%s.html" % self.type.replace(':', '-')], context, context_update)

    def pack(self):
        result = {
            'type': self.type,
            'uuid': self.uuid,

            'channel': self.channel,
            'author': self.author,
            'parent': self.parent,

            'created': self.created,
            'modified': self.modified or self.created,

            'url': self.url,
        }

        if self.order: result['order'] = self.order
        if self.value is not None: result['value'] = self.value
        if self.deleted: result['deleted'] = self.deleted
        if self.keys: result['keys'] = list(self.keys)
        if self.tags: result['tags'] = list(self.tags)
        if self.html: result['html'] = self.html

        if self.attachments: 
            result['attachments'] = self.attachments

        if self.data:
            if 'children' in self.data:
                result['data'] = dict(self.data)
                result['data']['children'] = [c.pack() for c in self.data['children'] if c is not None]
            else:
                result['data'] = simple( self.data )

        return result

    def unpack(self, state):
        # Get channel
        self.channel = state['channel']
        if isinstance( self.channel, models.Model ):
            self.channel, self._channel = self.channel.id, self.channel

        # Get author
        self.author = state['author']
        if isinstance( self.author, basestring ):
            try:
                self.author = from_json(self.author)
            except ValueError:
                self.author = None
        elif isinstance( self.author, models.Model ):
            self.author, self._author = self.author.simple(), self.author

        # Get parent
        self.parent = state.get('parent', None)
        if isinstance( self.parent, models.Model ):
            self.parent = self.parent.uuid
        if isinstance( self.parent, MessageType ):
            self.parent, self._parent = self.parent.uuid, self.parent

        self.order = state.get('order', 0)
        self.value = state.get('value', 0)

        self.created = to_datetime(state.get('created'), or_now=True)
        self.modified = to_datetime(state.get('modified'), or_now=True)
        self.deleted = bool(state.get('deleted', None))

        if state.get('status') == 'deleted':
            self.deleted = True

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
        record.modified = timezone.now()
        record.deleted = timezone.now() if self.deleted else None
        record.order = self.order
        record.value = self.value
        
        record.keys = " ".join(self.keys)
        record.tags = " ".join(self.tags)
        record.content = simple( self.data )

        if update_relations:
            record.channel = self.get_channel()
            record.parent = self.get_parent_record()
            record.author = self.get_author()

            if record.parent:
                record.depth = record.parent.depth + 1

        # Save our record
        record._message = self
        self._record = record

        # Save
        record.save()

        # Resolve new attachments
        self.save_attachments()

        return record

    def save_attachments(self):
        if not hasattr(self, '_attachment_objects'):
            return

        for attachment in self._attachment_objects:
            attachment.message = self.get_record()
            attachment.save()


    def attach(self, file):
        mimetype = file.content_type or getattr(file, 'mimetype', mimetypes.guess_type(file.name)[0])

        a = Attachment(
            uuid = uuid4().hex,
            mimetype =  mimetype or 'application/octet-stream',
            filename = file.name,
            source = file
        )

        a.save()

        if not hasattr(self, '_attachment_objects'):
            self._attachment_objects = []
            self._attachment_data = []
        self._attachment_objects.append(a)

        simple = a.simple()
        simple['size'] = file.size
        self.attachments.append(simple)

        return simple

    def broadcast(self):
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
            self._channel = channel_for(self.channel)
        return self._channel

    def get_channel_anchor(self):
        return self.get_channel().get_anchor()

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
            if self.author is None:
                self._author = None
            else:
                self._author = get_user_model().objects.get(pk=self.author['id'])
        return self._author

    def get_record(self):
        if not hasattr(self, '_record'):
            self._record = Message.objects.get(uuid=self.uuid)
        return self._record

    def get_edit_info(self):
        """Return the data needed to edit the message via the front-end."""
        info = {
            'form': self.type,
            'type': 'edit',
            'parent': self.uuid
        }
        for k, v in self.data.items():
            if k != 'children':
                info['data-' + k] = v
        return info

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
        try:
            if isinstance(state, MessageType):
                return state
            if isinstance(state, basestring):
                state = from_json(state)
            message = MessageType(type=state['type'], uuid=state['uuid'])
        except:
            return None
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



class Attachment(models.Model):
    uuid = UUIDField(auto=False, primary_key=True)
    message = models.ForeignKey(Message, related_name="attachments", blank=True, null=True)
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
            'filename_hash': self.filename_hash,
        }

    @property
    def filename_hash(self):
        return hash(self.filename)

    @property
    def url(self):
        return reverse('discourse:attachment', args=[self.message.channel.id, self.uuid, self.filename])


def library(messages):
    """
    Play through messages to get the current list of attachments.
    """
    by_name = {}
    meta = {}
    return []

    for message in messages:
        if message.type == 'attachment:meta':
            meta.setdefault(message.data['filename'].lower(), {}).update(message.data['meta'])
        if message.type == 'attachment:link':
            pass
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


_channel_cache = {}
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

    if id not in _channel_cache:
        try:
            _channel_cache[id] = Channel.objects.get(id=id)
        except Channel.DoesNotExist:
            _channel_cache[id] = Channel(id=id)
    return _channel_cache[id]



def channel_view(request, id, message_id=None):
    print "METHOD", request.method
    print "GET", request.GET
    print "POST", request.POST
    print "FILES", request.FILES

    channel = channel_for(id)
    inform = False

    if request.META.get('HTTP_X_JINJA') == 'true':
        print "JINJA", True
        JINJA = True
    else:
        JINJA = False
        print "JINJA", False

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
            if k.startswith('data['):
                data[k[5:-1]] = v

        parent = request.POST.get('parent', None)
        if parent:
            parent = get_object_or_404(Message, pk=parent)
        else:
            parent = None

        attachments = None
        if request.FILES:
            attachments = request.FILES.getlist('attachment')
        
        message = channel.publish(type, request.user, tags=tags, data=data, parent=parent, attachments=attachments, save=True, jinja=JINJA)
        return message.post(request)

    type = expand_tags(request.GET.getlist('type[]'))
    require_any = expand_tags(request.GET.getlist('require_any[]'))
    require_all = expand_tags(request.GET.getlist('require_all[]'))
    require_not = expand_tags(request.GET.getlist('require_not[]'))
    after = request.GET.get('after')
    deleted = request.POST.get('deleted') in ('true', 'yes', 'on', 'True')

    sort = request.GET.get('sort', 'recent')
    template = request.GET.get('template', None)

    messages = channel.search(type=type, require_any=require_any, require_all=require_all, require_not=require_not, sort=sort, deleted=deleted)
    return HttpResponse(channel.render_to_string(locals(), messages=messages, template=template))


def expand_tags(tags):
    if not tags:
        return None
    results = []
    for t in tags:
        results.extend( t.split() )
    return filter(None, [x.strip() for x in results]) or None


def attachment(request, channel, attachment, filename):
    channel = channel_for(channel)

    #if (request.method == 'POST' and request.POST.get('delete')) or request.method == 'DELETE':
    #    message = channel.set_attachment_meta(request.user, attachment, deleted=True)
    #    return JsonResponse( message.pack() )
    #
    #if (request.method == 'POST' and 'hidden' in request.POST):
    #    hidden = request.POST.get('hidden') in ('true', 'True', 'yes', '1')
    #    message = channel.set_attachment_meta(request.user, attachment, hidden=hidden)
    #    return JsonResponse( message.pack() )
    #
    #    message = channel.set_attachment_meta(request.user, attachment, hidden=(request.POST.get('hidden') == 'true'))

    attachment = channel.download(request.user, attachment, filename)

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
        
        tag_data = like(context, self.get_parent())
        with context.push( tag_data ):
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


class Flag(MessageType):
    def get_flags_set(self, parent):
        flags = parent.data.get('flags', None)
        if not isinstance(flags, dict):
            flags = parent.data['flags'] = {}

        name = self.data['name']
        flags[name] = set(flags.get(name, ()))
        return flags[name]

    def apply(self, parent): 
        if not 'name' in self.data:
            return

        if not isinstance(parent.data, dict):
            return 

        user_id = unicode(self.author['id'])

        flags = self.get_flags_set(parent)

        if self.data.get('remove'):
            if user_id not in flags:
                return
            flags.discard(user_id)
            value = -1
        else:
            if user_id in flags:
                return
            flags.add(user_id)
            value = 1

        parent.value += self.data.get('value', value)

    def post(self, request):
        from discourse.templatetags.discourse import like
        context = RequestContext(request)
        m = self.get_parent()
        packed = self.pack()
        if self.data.get('name'):
            packed['active'], packed['people'] = FlagStringer(self.data['name'])(m, request.user)
        return JsonResponse(packed)


class FlagStringer(object):
    one = '<a href="#">1 person</a>'
    many = '<a href="#">{} people</a>'
    no_people = ""
    one_other = '<a href="#">1 other</a>'
    many_others = '<a href="#">{} others</a>'
    you = '<span class="you">You</span>'
    conjunction = "and"

    def __init__(self, name, **kwargs):
        self.name = name
        self.end = '<span>' + name + 's</span>'
        self.ends = '<span>' + name + '</span>'
        self.__dict__.update(kwargs)

    def __call__(self, message, user):
        set = self.get_flag_set(message)
        if not set:
            return False, self.no_people
        parts = []
        total = len(set)
        
        one = self.one
        many = self.many
        you = False
        end = self.end
        
        if user.is_authenticated() and unicode(user.id) in set:
            parts.append(self.you)
            total -= 1
            one = self.one_other
            many = self.many_others
            you = True
            end = self.ends
        
        if parts and total:
            parts.append(self.conjunction)

        if total == 1:
            parts.append(one)
        elif total > 1:
            end = self.ends
            parts.append(many.format(total))

        if parts:
            parts.append(end)

        return you, " ".join(parts)

    def get_flag_set(self, message):
        try:
            return set( message.data.get('flags', {}).get(self.name, ()) )
        except:
            return None


class Reply(MessageType):
    def apply(self, parent):
        parent.data.setdefault('children', []).append(self)

    def get_edit_info(self):
        info = super(Reply, self).get_edit_info()
        info['data-body'] = self.data['body']
        return info


class AttachmentType(MessageType):
    type = "attachment"

    def build(self):
        if not self.attachments:
            return

        attachment = self.attachments[0]
        self.data.update({
            'filename': attachment['filename'],
            'filename_hash': hash(attachment['filename']),
            'url': reverse('discourse:attachment', args=[self.channel, self.uuid, attachment['filename']]),
            'size': attachment.get('size', '?'),
            'mimetype': attachment['mimetype']
        })
        self.data['icon'] = self.icon
        return self.data

    @property
    def icon(self):
         """
         Returns the icon type for the file.
         """
         if "application/pdf" in self.data['mimetype']:
             return "icon-doc-text"
         elif "image/" in self.data['mimetype']:
             return "icon-doc"
         elif "application/msword" in self.data['mimetype']:
             return "icon-doc-text"
         elif "officedocument" in self.data['mimetype']:
             return "icon-doc-text"
         elif self.data['filename'].endswith(".pages"):
             return "icon-doc-text"
         return "icon-doc"

    def thumbnail(self):
        return '<i class="{}"></i> '.format(self.icon)


class AttachmentMeta(MessageType):
    type = "attachment:meta"

    def apply(self, other):
        other.data.update(self.data)


class AttachmentLink(MessageType):
    type = "attachment:link"

    def build(self):
        self.data.update({
            'filename': self.data.get('filename', self.data['url']),
            'filename_hash': hash(self.data['url']),
            'size': 0,
            'mimetype': 'text/url'
        })
        if '://' not in self.data['url']:
            self.data['url'] = 'http://' + self.data['url']
        return self.data

    def thumbnail(self):
        return '<i class="icon-link-ext-alt"></i> '



class Delete(MessageType):
    type = "delete"

    def apply(self, other):
        other.deleted = True


class Tag(MessageType):
    def apply(self, other):
        if 'set' in self.data:
            other.tags = self.get_data_tags('set')
        other.tags |= self.get_data_tags('add')
        other.tags -= self.get_data_tags('remove')
        print other.tags

    def get_data_tags(self, k):
        tags = self.data.get(k)
        if not tags:
            return set()
        if isinstance(tags, basestring):
            return set([tags])
        return set(tags)


class Edit(MessageType):
    def apply(self, other):
        other.data.update(self.data)

    def post(self, request):
        return self.get_parent().post(request)

    def emit(self, socket, context):
        self.apply(self.get_parent())
        return self.get_parent().emit(socket, context)


#class AttachmentMeta(MessageType):
#    type = "attachment:meta"
#    def apply(self, parent):
#        pass
#        #parent.data.setdefault(self.data['filename'].lower(), {}).update(self.data['meta'])
#        #parent.data.update(self.data)
#
#