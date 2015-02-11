import redis, json
from socketio.namespace import BaseNamespace
from discourse.models import Comment
from django.conf import settings


class DiscourseSocket(BaseNamespace):
    def initialize(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=getattr(settings, 'REDIS_DB', 1))

    def follow_loop(self, path):
        o = self.redis.pubsub()
        o.subscribe([path])
        for item in o.listen():
            if item.get('type') == 'message':
                data = json.loads(item['data'])
                if data.get('predicate'):
                    self.emit(data['predicate'], data)

    def on_follow(self, path):
        self.spawn(self.follow_loop, path)
