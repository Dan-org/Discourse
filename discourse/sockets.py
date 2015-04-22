import redis, json
from socketio.namespace import BaseNamespace
from django.conf import settings
from django.template import Context, RequestContext

from discourse.message import MessageType


class DiscourseSocket(BaseNamespace):
    def initialize(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=getattr(settings, 'REDIS_DB', 1))

    def follow_loop(self, path):
        render_context = RequestContext(self.request, {})
        o = self.redis.pubsub()
        print "FOLLOWING", path
        o.subscribe([path])
        for item in o.listen():
            if item.get('type') == 'message':
                m = MessageType.rebuild(json.loads(item['data']))
                m.html = m.render(render_context)
                self.emit(m.type, m.pack())

    def on_follow(self, path):
        self.spawn(self.follow_loop, path)
