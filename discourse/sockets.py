import redis, json
from socketio.namespace import BaseNamespace
from django.conf import settings
from django.template import Context, RequestContext

from discourse.message import MessageType, channel_for


class DiscourseSocket(BaseNamespace):
    def initialize(self):
        self.redis = redis.Redis(host=getattr(settings, 'REDIS_HOST', 'localhost'), port=6379, db=getattr(settings, 'REDIS_DB', 1))

    def follow_loop(self, path):
        if not self.request:
            print "SocketIO Namespace has no .request property."
            return self.disconnect()
        render_context = RequestContext(self.request, {'request': self.request})
        if self.request.GET.get('JINJA') == 'true':
            render_context['JINJA'] = True
        o = self.redis.pubsub()
        o.subscribe([path])
        for item in o.listen():
            if item.get('type') == 'message':
                m = MessageType.rebuild(json.loads(item['data']))
                m.emit(self, render_context)

    def on_follow(self, path):
        self.spawn(self.follow_loop, path)

    def on_message(self, channel, kwargs):
        channel = channel_for(channel)
        kwargs.setdefault('jinja', True)
        kwargs.setdefault('save', False)
        channel.publish(**kwargs)