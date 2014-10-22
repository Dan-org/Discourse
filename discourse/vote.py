from django.db import transaction
from django.db import models
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

from ajax import JsonResponse
from event import publish
from uri import uri, resolve_model_uri


class Vote(models.Model):
    target_uri = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="votes")
    value = models.IntegerField()

    class Meta:
        app_label = 'discourse'

    def __unicode__(self):
        if self.value > 0:
            return "Upvote by %s" % self.user
        elif self.value < 0:
            return "Downvote by %s" % self.user
        else:
            return "Sidevote by %s" % self.user

    @property
    def target(self):
        return resolve_model_uri(self.target_uri)[0]

    @classmethod
    def value_for(cls, target, user=None):
        target = uri(target)
        if user and user.is_authenticated():
            try:
                return cls.objects.get(target_uri=target, user=user).value
            except cls.DoesNotExist:
                return 0
        return ( cls.objects.filter(target_uri=target).aggregate(models.Sum('value'))['value__sum'] or 0 )

    @classmethod
    def cast(cls, user, target, value):
        vote, created = cls.objects.get_or_create(user=user, target_uri=uri(target), defaults={'value': value})
        if not created:
            vote.value = value
            vote.save()
        return vote


### Views ###
@login_required
def cast(request, uri):
    if not request.POST:
        return HttpResponseBadRequest()

    direction = request.POST.get('direction', '').lower()

    if direction == 'up':
        value = 1
    elif direction == 'down':
        value = -1
    elif direction == 'reset':
        value = 0
    else:
        return HttpResponseBadRequest("'direction' must be 'up', 'down', or 'reset', not %r" % direction)

    event = publish(uri, request.user, 'vote:before', data={'value': value}, internal=True)
    if not event:
        raise PermissionDenied()

    vote = Vote.cast(request.user, uri, event.data['value'])

    event = publish(uri, request.user, 'vote', data={'value': vote.value})    

    return JsonResponse(Vote.value_for(uri))
