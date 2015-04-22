import ttag
from uuid import uuid4
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from message import channel_for


def stream_tag(context, channel, type='comment', size=21, tags=None, sort="recent", template='discourse/stream.html', id=None, deleted=False):
    if type and isinstance(type, basestring):
        type = [x.strip() for x in type.split() if x.strip()]

    if tags and isinstance(tags, basestring):
        tags = [x.strip() for x in tags.split() if x.strip()]

    channel = channel_for(channel)
    messages = channel.search(type=type, tags=tags, sort=sort, deleted=deleted)

    context['stream_id'] = id or uuid4().hex
    return channel.render_to_string(context, messages, template=template)


def library_tag(context, channel, size=21, tags=None, sort="filename", template='discourse/library.html', id=None, deleted=False):
    if tags and isinstance(tags, basestring):
        tags = [x.strip() for x in tags.split() if x.strip()]

    channel = channel_for(channel)
    messages = channel.search(type='attachment', tags=tags, sort='recent', deleted=deleted)

    by_filename = {}
    for message in messages:
        print "DELETED", message.deleted
        if message.type != 'attachment' or (message.deleted and not deleted):
            continue
        by_filename.setdefault(message.data['filename_hash'], message)

    messages = list( by_filename.values() )
    if sort == 'recent':
        messages.sort(key=lambda m: m.created, reversed=True)
    if sort == 'filename':
        messages.sort(key=lambda m: m.data['filename'])
    elif sort == 'likes':
        messages.sort(key=lambda m: m.value)

    context['library_id'] = id or uuid4().hex
    return channel.render_to_string(context, messages, template=template)