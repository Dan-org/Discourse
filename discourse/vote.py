from django.db import models
from django.conf import settings
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

