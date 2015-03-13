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


from ..thread import ThreadTag, ThreadCountTag
from ..library import LibraryTag
from ..document import DocumentTag
from ..event import StreamTag
from ..follow import FollowTag
from ..favorite import FavoriteTag

register = template.Library()
register.tag(ThreadTag)
register.tag(ThreadCountTag)
register.tag(LibraryTag)
register.tag(DocumentTag)
register.tag(StreamTag)
register.tag(Uri)
register.tag(FollowTag)
register.tag(FavoriteTag)


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


