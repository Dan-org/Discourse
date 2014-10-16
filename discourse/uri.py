import re, urllib, time, posixpath
from django.db import models

__all__ = ['uri', 'resolve_model_uri', 'simple']


re_model_uri = re.compile(r"model\://([^/]+)/([^/]+)/([^/]+)(/.*)?")         # i.e. model://<app>/<model>/<pk> [/<rest>]


def uri(obj, rest=None):
    if isinstance(obj, basestring):
        uri = obj
    elif hasattr(obj, 'uri'):
        if iscallable(obj.uri):
            uri = obj.uri()
        else:
            uri = obj.uri
    elif isinstance(obj, models.Model):
        cls = obj.__class__
        app = cls._meta.app_label      # auth
        model = cls._meta.model_name   # User
        pk = str( obj._get_pk_val() )    # 7
        uri = "model://%s/%s/%s" % ( urllib.quote(app), urllib.quote(model), urllib.quote(pk) )
    if rest is not None:
        return posixpath.join(uri, urllib.quote(rest))
    else:
        return uri


def resolve_model_uri(uri):
    m = re_model_uri.match(uri)
    if m is None:
        return None, uri
    app, model, pk, rest = m.groups()
    cls = get_model( urllib.unquote(app), urllib.unquote(model) )
    obj = cls.objects.get(pk=urllib.unquote(pk))
    if rest is None:
        return obj, None
    else:
        return obj, urllib.unquote(rest[1:])


def simple(object):
    if hasattr(object, 'simple'):
        return object.simple()
    elif isinstance(object, list):
        return [simple(x) for x in list]
    elif isinstance(object, tuple):
        return tuple(simple(x) for x in list)
    elif isinstance(object, dict):
        return dict((k, simple(v)) for k, v in object.items())
    elif isinstance(object, datetime):
        return time.mktime(object.timetuple())
    return object

