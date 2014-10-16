from django.db import models
from django.conf import settings
from uri import *


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    target_uri = models.CharField(max_length=255)
    toggle = models.BooleanField(default=True)

    def __unicode__(self):
        return "Subscription(%r, %r, toggle=%r)" % (self.user, self.uri, self.toggle)

    class Meta:
        app_label = 'discourse'



def follow(user, target, force=False):
    """
    Subscribe a user to a target, thereon whenever an update occurs on there, the user will be
    notified of the event.
    """
    sub, _ = Subscription.objects.get_or_create(user=user, target_uri=uri(target))
    if force:
        sub.toggle = True
        sub.save()


def unfollow(user, target):
    """
    Unsubscribe a user from a target, blocking notices of updates on it.  This is not as simple as
    deleting the subscription object, rather it marks them unsubscribed so that futher subscriptions
    are ignored.
    """
    target_uri = uri(target)
    hits = Subscription.objects.filter(user=user, target_uri=target_uri).update(toggle=False)
    if hits == 0:
        Subscription.objects.create(user=user, target_uri=target_uri, toggle=False)
    return True


def is_following(user, target):
    """
    Checks to see if a user is subscribed to the given target.
    """
    return Subscription.objects.filter(user=user, target_uri=uri(target), toggle=True).count() > 0


def get_subscriptions(*targets):
    targets = [uri(t) for t in targets if t]
    return Subscription.objects.filter(target_uri__in=targets, toggle=True)


def get_followers(*targets):
    return set([s.user for s in get_subscriptions(*targets)])


def get_follower_count(*targets):
    return get_subscriptions(*targets).count()

