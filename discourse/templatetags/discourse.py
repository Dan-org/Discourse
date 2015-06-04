import urllib, json, re
from pprint import pprint

from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
from django import template

from ..ajax import to_json

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

#from ..library import LibraryTag
from ..follow import FollowTag
from ..favorite import FavoriteTag
from ..document import DocumentTag
from ..message import channel_for

register = template.Library()
#register.tag(LibraryTag)
register.tag(FollowTag)
register.tag(FavoriteTag)
register.tag(DocumentTag)

from ..stream import stream_tag, library_tag
register.simple_tag(takes_context=True, name="stream")(stream_tag)
register.simple_tag(takes_context=True, name="library")(library_tag)


@register.simple_tag
def channel(obj):
    return channel_for(obj).url


@register.inclusion_tag("discourse/likes.html", takes_context=True)
def like(context, message, show=2):
    try:
        likes = set( message.data.get('likes', []) )
    except:
        likes = set()

    authenticated = True
    user = None
    if 'request' in context:
        user = context['request'].user
    elif 'user' in context:
        user = context['user']

    if not likes:
        return {
            'authenticated': user.is_authenticated() if user else None,
            'user': user,
            'message': message,
            'liked': False,
            'count': 0
        }

    parts = []
    liked = False
    if user.id in likes or str(user.id) in likes:
        liked = True
        likes.discard(user.id)
        likes.discard(str(user.id))
        parts.append('<a href="%s">You</a>' % user.get_absolute_url())
    
    for id in list(likes)[:show]:
        u = get_user_model().objects.get(pk=id)
        parts.append('<a href="{}">{}</a>'.format(u.get_absolute_url(), u.get_full_name()))

    if len(likes) > show:
        parts.append("{} more".format(len(likes) - show))

    if len(parts) > 1:
        parts[-1] = "and %s" % parts[-1]

    if len(parts) > 2:
        parts = ", ".join(parts)
    else:
        parts = " ".join(parts)

    return {
        'authenticated': user.is_authenticated() if user else None,
        'user': user,
        'message': message,
        'liked': liked,
        'likes': mark_safe( parts ),
        'count': len(likes)
    }


### Filters ###
@register.filter(is_safe=True, name="to_json")
def json_filter(value):
    return mark_safe(to_json(value))


re_hash = re.compile(r'\b\#\w[-_\w]+\w')
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


