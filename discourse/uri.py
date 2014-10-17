import re, urllib, time, posixpath, decimal
from datetime import datetime
from django.db import models

__all__ = ['uri', 'resolve_model_uri', 'simple']


re_model_uri = re.compile(r"([^/]+)/([^/]+)/([^/]+)(/.*)?")         # i.e. /<app>/<model>/<pk> [/<rest>]


def uri(obj, rest=None):
    uri = obj
    if isinstance(obj, models.Model):
        cls = obj.__class__
        app = cls._meta.app_label      # auth
        model = cls._meta.model_name   # User
        pk = str( obj._get_pk_val() )    # 7
        uri = "%s/%s/%s" % ( urllib.quote(app), urllib.quote(model), urllib.quote(pk) )
    
    if rest is not None:
        return posixpath.join(uri, urllib.quote(rest))
    else:
        return uri


def resolve_model_uri(uri):
    m = re_model_uri.match(uri)
    if m is None:
        return None, uri
    app, model, pk, rest = m.groups()
    cls = models.get_model( urllib.unquote(app), urllib.unquote(model) )
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
    elif isinstance(object, basestring):
        return object
    elif isinstance(object, float):
        return object
    elif isinstance(object, int):
        return object
    else:
        return unicode( object )

