import datetime, logging
from collections import defaultdict
from pprint import pprint, pformat

try:
    from django.template import Context
except ImportError:                                 # version < 1.8
    from django.template.loader import Context

from django.template.loader import render_to_string, TemplateDoesNotExist, select_template
from django.conf import settings
from haystack import indexes
from haystack.query import SearchQuerySet
from message import Message

from ajax import to_json

log = logging.getLogger('discourse')

def clean_uuid(uuid):
    if uuid:
        return str(uuid).replace('-', '')
    return uuid


class MessageIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    type = indexes.CharField(model_attr='type')
    uuid = indexes.CharField(model_attr='uuid')
    channel = indexes.CharField(model_attr='channel_id')
    order = indexes.IntegerField(model_attr='order')
    parent = indexes.CharField(model_attr='parent_id', null=True)
    created = indexes.DateTimeField(model_attr='created')
    modified = indexes.DateTimeField(model_attr='modified', null=True)
    deleted = indexes.BooleanField(model_attr='deleted', null=True)
    status = indexes.CharField()
    url = indexes.CharField(model_attr='url', indexed=False)
    value = indexes.IntegerField(default=0)

    author = indexes.CharField()
    keys = indexes.MultiValueField()
    tags = indexes.MultiValueField()
    attachments = indexes.CharField(null=True)
    data = indexes.CharField(indexed=False, model_attr='content', null=True)

    def get_children(self, message):
        children = getattr(message, 'children', None)
        if children is not None:
            return children
        cache = getattr(self, 'children_index', {})
        return cache.get(clean_uuid(message.uuid), ())

    def cache_as_child(self, message):
        if not hasattr(self, 'children_index'):
            self.children_index = {}
        if not message.parent_id:
            return
        self.children_index.setdefault(clean_uuid(message.parent_id), []).append(message)

    def update(self, using=None):
        self.children_index = {}
        super(MessageIndex, self).update(using)

    def get_model(self):
        return Message

    def build_queryset(self, *a, **ka):
        result = super(MessageIndex, self).build_queryset(*a, **ka)
        self.build_child_index()
        return result

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        print "INDEX QUERYSET"
        return self.get_model().objects.filter(parent=None).order_by('depth', 'order', 'created').select_related('author')

    def build_child_index(self):
        print "BUILDING CHILD INDEX..."
        self.children_index = defaultdict(list)
        for obj in self.get_model().objects.exclude(parent=None).order_by('parent_id', 'depth', 'order', 'created').select_related('author'):
            self.children_index[clean_uuid(obj.parent_id)].append(obj)
        print "DONE", len(self.children_index)

    def get_updated_field(self):
        return 'modified'

    def update_object(self, instance, using=None):
        if not self.should_update(instance):
            return False

        backend = self._get_backend(using)
        if backend is None:
            return

        top = instance
        try:
            while top.parent:
                top = top.parent
        except Message.DoesNotExist:
            pass

        todo = [top]
        instances = []
        while todo:
            instances.extend(todo)
            todo = list( Message.objects.filter(parent__uuid__in=[x.uuid for x in todo]) )

        instances.reverse()

        for instance in instances:
            self.cache_as_child(instance)

        backend.update(self, instances)

    def prepare_text(self, message):
        return repr(message.content)

    def prepare(self, message):
        state = super(MessageIndex, self).prepare(message)

        message = message.rebuild()
        message.children = self.get_children(message)

        # Iterate through each child and have it apply() itself to its parent.
        seen = set()
        for child in message.children:
            if child.uuid in seen:
                continue
            seen.add(child.uuid)
            child = child.rebuild()
            if not child.deleted:
                child.apply(message)

        message.prepare()

        data = message.pack()
        state.update(data)

        for key in ['author', 'data', 'attachments']:
            fix_json(state, key)

        if not state.get('deleted'):
            state['status'] = 'alive'
        else:
            state['status'] = 'deleted'

        try:
            state['text'] = render_to_string('discourse/index/%s.txt' % message.type, locals())
        except TemplateDoesNotExist:
            pass
        
        #if settings.DEBUG:
        #   log.debug(pformat(state))
        if state['uuid']:
            state['uuid'] = clean_uuid(state['uuid'])

        if state['parent']:
            state['parent'] = clean_uuid(state['parent'])

        return state


def fix_json(state, key):
    if state.get(key, None):
        state[key] = to_json(state[key])
    else:
        state[key] = None
