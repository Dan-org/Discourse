from models import *
from follow import follow, unfollow, get_followers, get_follower_count
from message import channel_for, MessageType, on
from uri import uri, resolve_model_uri, simple
from template import set_jinja_env

### Helpers ###
def template_repr(var):
    r = repr(var)
    if r.startswith('u"') or r.startswith("u'"):
        return r[1:]
    return r

def tag_repr(name, *args, **kwargs):
    parts = [name]
    if args:
        parts.extend(args)
    if kwargs:
        parts.extend(["%s=%s" % (k, template_repr(v)) for k, v in kwargs.items() if v is not None])
    return "{%% %s %%}" % " ".join(parts)
