import ttag
from uuid import uuid4
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from message import channel_for


def stream_tag(context, channel, type='comment', size=21, require_any=None, require_all=None, sort="recent", template='discourse/stream.html', id=None, deleted=False, inform=False):
    if type and isinstance(type, basestring):
        type = [x.strip() for x in type.split() if x.strip()]

    if require_any and isinstance(require_any, basestring):
        require_any = [x.strip() for x in require_any.split() if x.strip()]

    if require_all and isinstance(require_all, basestring):
        require_all = [x.strip() for x in require_all.split() if x.strip()]

    channel = channel_for(channel)
    messages = channel.search(type=type, require_any=require_any, require_all=require_all, sort=sort, deleted=deleted)

    context['stream_id'] = id or uuid4().hex
    context['type'] = " ".join(type or [])
    context['require_any'] = " ".join(require_any or [])
    context['require_all'] = " ".join(require_all or [])
    context['inform'] = inform
    return channel.render_to_string(context, messages, template=template)


def library_tag(context, channel, size=21, require_any=None, require_all=None, sort="filename", template='discourse/library.html', id=None, deleted=False):
    if require_any and isinstance(require_any, basestring):
        require_any = [x.strip() for x in require_any.split() if x.strip()]

    if require_all and isinstance(require_all, basestring):
        require_all = [x.strip() for x in require_all.split() if x.strip()]

    channel = channel_for(channel)
    messages = channel.search(type=['attachment', 'attachment:link'], require_any=require_any, require_all=require_all, sort='recent', deleted=True)
    
    messages = channel.get_attachments(messages, deleted=deleted)

    if sort == 'recent':
        messages.sort(key=lambda m: m.created, reversed=True)
    if sort == 'filename':
        messages.sort(key=lambda m: m.data['filename'])
    elif sort == 'likes':
        messages.sort(key=lambda m: m.value)

    context['require_any'] = " ".join(require_any or [])
    context['require_all'] = " ".join(require_all or [])
    context['library_id'] = id or uuid4().hex
    return channel.render_to_string(context, messages, template=template)