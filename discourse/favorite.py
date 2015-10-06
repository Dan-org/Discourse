from . import follow
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from uri import *
from ajax import JsonResponse


class Favorite(follow.Subscription):
    class Meta:
        app_label = 'discourse'

favorite = Favorite.follow
unfavorite = Favorite.unfollow
is_favorited = Favorite.is_following
get_favorites = Favorite.get_subscriptions
get_favorited = Favorite.get_subscribed
get_favorited_by = Favorite.get_followers
get_favorited_count = Favorite.get_follower_count


### Template Tags ###
import ttag
from django.template.loader import render_to_string


class FavoriteTag(ttag.Tag):
    """
    Creates a follow button for the given path
    """
    anchor = ttag.Arg(required=True)

    class Meta:
        name = "favorite"

    def render(self, context):
        request = context['request']
        data = self.resolve(context)
        anchor = uri(data['anchor'])
        
        url = reverse("discourse:favorite")
        if request.user.is_authenticated():
            subscribed = is_favorited(request.user, anchor)
        else:
            subscribed = False
        return render_to_string('discourse/favorite.html', locals())


### Views ###
@login_required
def manipulate(request):
    if not request.POST:
        return HttpResponseBadRequest()

    target = request.POST['uri']

    if request.POST.get('unfavorite', '').lower() in ('yes', 'true'):
        unfavorite(request.user, target)
    else:
        favorite(request.user, target, True)

    return JsonResponse(get_favorited_count(target))


