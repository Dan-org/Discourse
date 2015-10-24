from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from uri import uri, resolve_model_uri
from ajax import JsonResponse


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    target_uri = models.CharField(max_length=255)
    toggle = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s(%r, %r, toggle=%r)" % (self.__class__.__name__, self.user, self.target_uri, self.toggle)

    class Meta:
        app_label = 'discourse'

    @property
    def target(self):
        try:
            obj, _uri = resolve_model_uri(self.target_uri)
        except:
            return None
        return obj

    @classmethod
    def follow(cls, user, target, force=False):
        """
        Subscribe a user to a target, thereon whenever an update occurs on there, the user will be
        notified of the event.
        """
        try:
            sub = cls.objects.filter(user=user, target_uri=uri(target))[0]
        except IndexError:
            sub = cls.objects.create(user=user, target_uri=uri(target))
        if force:
            sub.toggle = True
            sub.save()

    @classmethod
    def unfollow(cls, user, target):
        """
        Unsubscribe a user from a target, blocking notices of updates on it.  This is not as simple as
        deleting the subscription object, rather it marks them unsubscribed so that futher subscriptions
        are ignored.
        """
        target_uri = uri(target)
        hits = cls.objects.filter(user=user, target_uri=target_uri).update(toggle=False)
        if hits == 0:
            cls.objects.create(user=user, target_uri=target_uri, toggle=False)
        return True

    @classmethod
    def is_following(cls, user, target):
        """
        Checks to see if a user is subscribed to the given target.
        """
        return cls.objects.filter(user=user, target_uri=uri(target), toggle=True).count() > 0

    @classmethod
    def get_subscriptions(cls, *targets):
        targets = [uri(t) for t in targets if t]
        return cls.objects.filter(target_uri__in=targets, toggle=True)

    @classmethod
    def get_subscribed(cls, user, target_cls):
        target_uri = uri(target_cls) + "."
        return cls.objects.filter(target_uri__startswith=target_uri, user=user, toggle=True)

    @classmethod
    def get_followers(cls, *targets):
        return set([s.user for s in cls.get_subscriptions(*targets)])

    @classmethod
    def get_follower_count(cls, *targets):
        return cls.get_subscriptions(*targets).count()

follow = Subscription.follow
unfollow = Subscription.unfollow
is_following = Subscription.is_following
get_subscriptions = Subscription.get_subscriptions
get_subscribed = Subscription.get_subscribed
get_followers = Subscription.get_followers
get_follower_count = Subscription.get_follower_count


### Template Tags ###
import ttag
from django.template.loader import render_to_string


class FollowTag(ttag.Tag):
    """
    Creates a follow button for the given path
    """
    anchor = ttag.Arg(required=True)

    class Meta:
        name = "follow"

    def render(self, context):
        request = context['request']
        data = self.resolve(context)
        anchor = uri( data['anchor'] )
        
        url = reverse("discourse:follow")
        if request.user.is_authenticated():
            subscribed = is_following(request.user, anchor)
        else:
            subscribed = False
        return render_to_string('discourse/follow.html', locals())


### Views ###
@login_required
def manipulate(request):
    if not request.POST:
        return HttpResponseBadRequest()

    target_uri = uri(request.POST['uri'])

    if request.POST.get('unfollow', '').lower() in ('yes', 'true'):
        unfollow(request.user, target_uri)
    else:
        follow(request.user, target_uri, True)

    return JsonResponse(get_follower_count(target_uri))


