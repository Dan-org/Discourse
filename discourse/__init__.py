from notice import subscribe, unsubscribe, is_subscribed, send_event, render_mail, send_render_mail

from models import (model_sig,
                    get_instance_from_sig,
                    comment_manipulate,
                    attachment_manipulate,
                    document_manipulate,
                    library_view,
                    document_view,
                    attachment_view,
                    comment_vote,
                    event)

from notice import send_event


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