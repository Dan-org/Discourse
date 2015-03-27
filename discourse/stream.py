import ttag
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from message import channel_for


typeof = type

def stream_tag(context, channel, type=None, size=21, tags=None, template='discourse/stream.html'):
    if type:
        type = [x.strip() for x in type.split(',') if x.strip()]

    if tags:
        tags = [x.strip() for x in tags.split(',') if x.strip()]

    channel = channel_for(channel)

    return channel.render_to_string(context, type=type, tags=tags)
