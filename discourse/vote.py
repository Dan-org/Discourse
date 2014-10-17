from django.db import models
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

from ajax import JsonResponse
from event import publish
from uri import uri


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

    @classmethod
    def value_for(cls, target, user=None):
        target = uri(target)
        if user:
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
def vote(request):
    if not request.POST:
        return HttpResponseBadRequest()

    uri = request.POST.get('uri')
    direction = request.POST.get('direction', '').lower()

    if direction not in ('up', 'down', 'reset'):
        return HttpResponseBadRequest("'value' most be an integer")

    event = publish(uri, request.user, 'vote', data={'value': value})
    if not event:
        raise PermissionDenied()

    Vote.cast(request.user, uri, event.data['value'])
    return JsonResponse(Vote.value_for(uri))
