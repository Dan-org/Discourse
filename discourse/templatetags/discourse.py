import urllib, json, re

from django.utils.safestring import mark_safe
from django import template

import ttag


### Template Tags ###
class Uri(ttag.Tag):
    """
    Returns the discourse path associated with the object given as the first argument.
    """
    anchor = ttag.Arg(required=True)
    sub = ttag.Arg(default=None, keyword=True, required=False)          # Optional sub-document

    class Meta:
        name = "uri"

    def render(self, context):
        data = self.resolve(context)
        anchor = uri(data.get('anchor'), data.get('sub'))
        return uri(context)


#from ..thread import ThreadTag, ThreadCountTag
#from ..library import LibraryTag
#from ..document import DocumentTag
#from ..event import StreamTag
#
#
#register = template.Library()
#register.tag(ThreadTag)
#register.tag(ThreadCountTag)
#
#register.tag(DocumentTag)
#register.tag(StreamTag)
#register.tag(Uri)

from ..library import LibraryTag
from ..follow import FollowTag
from ..favorite import FavoriteTag
from ..document import DocumentTag
from ..message import channel_for

register = template.Library()
register.tag(LibraryTag)
register.tag(FollowTag)
register.tag(FavoriteTag)
register.tag(DocumentTag)

from ..stream import stream_tag
register.simple_tag(takes_context=True, name="stream")(stream_tag)


@register.simple_tag
def channel(obj):
    return channel_for(obj).url


#@register.simple_tag(takes_context=True)
#def likes(message):
#    users = set()
#    for m in message.children.filter(type__in=['like', 'unlike']).select_related('author'):
#        if m.type == 'like':
#            users.add(m.author)
#        if m.type == 'unlike':
#            users.discard(m.author)
#
#    if not users:
#        return ''
#
#    users = list(users)
#
#    return ['<a href="%s">%s</a>' % (u.get_absolute_url(), u.get_full_name()) for u in users[:3]]
#
#    return users



### Filters ###
@register.filter(is_safe=True)
def to_json(value):
    return mark_safe(json.dumps(value))


re_hash = re.compile(r'\#\w[-_\w]+\w')
def hash_link(m):
    tag = m.group(0)
    name = tag.lstrip('#')
    return '<a name="{name}" class="hashtag" href="/search/?q={safe_name}">#{name}</a>'.format(
        safe_name = urllib.quote(tag),
        name = name,
    )

@register.filter(is_safe=True)
def hashtags(value):
    return mark_safe( re_hash.sub(hash_link, value) )


