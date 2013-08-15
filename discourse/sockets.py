import redis, json
from socketio.namespace import BaseNamespace
from discourse.models import Comment
from django.conf import settings


class DiscourseSocket(BaseNamespace):
    def initialize(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=settings.REDIS_DB)

    def follow_loop(self, path):
        o = self.redis.pubsub()
        o.subscribe([path])
        for item in o.listen():
            if item['type'] == 'message':
                item = json.loads(item['data'])
                print item
                if item['type'] == 'vote':
                    self.emit('vote', item)
                elif item['type'] == 'comment':
                    self.emit('comment', item['comment'])
                elif item['type'] == 'delete':
                    self.emit('delete', item['id'])

    def on_follow(self, path):
        self.spawn(self.follow_loop, path)