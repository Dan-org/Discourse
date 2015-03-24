import ttag
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from message import channel_for


class StreamTag(ttag.Tag):
    """
    Show a stream for an object
    {% stream object %}

    Show a stream for a string
    {% stream 'pandas' %}

    Set the initial size of shown events to 5 instead of the default of 21:
    {% stream object size=5 %}

    Filter to a certain type
    {% stream object type="comment" %}

    Or many types:
    {% stream object type="comment, cheer" %}

    Change the template:
    {% stream object template="discourse/feedback.html" %}

    """
    channel = ttag.Arg(required=True)
    size = ttag.Arg(required=False, keyword=True)
    tags = ttag.Arg(required=False, keyword=True)
    tempalte = ttag.Arg(required=False, keyword=True)

    def render(self, context):
        data = self.resolve(context)
        channel = channel_for(data['channel'])
        type = data.get('type')
        size = data.get('size', 21)
        tags = data.get('tags')
        template = data.get('template', 'discourse/stream.html')

        messages = channel.search(type=type, tags=tags)

        parts = []
        for m in messages:
            print m.type, m.uuid
            parts.append( m.render_to_string(context) )

        content = mark_safe("\n".join(parts))

        return render_to_string(template, locals(), context)

    class Meta:
        name = "stream"
