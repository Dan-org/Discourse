import datetime
from django.template.loader import render_to_string, TemplateDoesNotExist, Context, select_template
from haystack import indexes
from message import Message, apply_delta

from ajax import to_json


class MessageIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True)
    type = indexes.CharField(model_attr='type')
    uuid = indexes.CharField(model_attr='uuid')
    channel = indexes.CharField(model_attr='channel_id')
    order = indexes.IntegerField(model_attr='order')
    parent = indexes.CharField(model_attr='parent_id', null=True)
    author = indexes.CharField(model_attr='author_id')
    created = indexes.DateTimeField(model_attr='created')
    modified = indexes.DateTimeField(model_attr='modified')
    deleted = indexes.DateTimeField(model_attr='deleted', null=True)
    url = indexes.CharField(model_attr='url', indexed=False)
    html = indexes.CharField(indexed=False)
    
    value = indexes.IntegerField(default=0)
    keys = indexes.MultiValueField()
    tags = indexes.MultiValueField()
    data = indexes.CharField(indexed=False, model_attr='content', null=True)

    def get_model(self):
        return Message

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()

    def prepare_keys(self, message):
        if message.keys:
            return message.keys.split()
        return []

    def prepare_tags(self, message):
        return message.tags

    def prepare_value(self, message):
        return 0

    def prepare_text(self, message):
        try:
            return render_to_string('discourse/index/%s.txt' % message.type, locals())
        except TemplateDoesNotExist:
            return repr(message.data)

    def prepare(self, message):
        self.prepared_data = super(MessageIndex, self).prepare(message)

        self.prepared_data['data'] = message.data
        self.prepared_data['author'] = to_json(message.author)

        apply_delta(self.prepared_data, message)
        for child in message.children.all():
            apply_delta(self.prepared_data, child)
        
        self.prepared_data['data'] = to_json(self.prepared_data['data'])

        return self.prepared_data






