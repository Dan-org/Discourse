import ttag
from uuid import uuid4
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from message import channel_for


def stream_tag(context, channel, type='comment', size=21, tags=None, sort="recent", template='discourse/stream.html', id=None):
    if type:
        type = [x.strip() for x in type.split() if x.strip()]

    if tags:
        tags = [x.strip() for x in tags.split() if x.strip()]

    channel = channel_for(channel)

    context['stream_id'] = id or uuid4().hex

    return channel.render_to_string(context, type=type, tags=tags, sort=sort)
