from django.contrib import admin
from models import Page

admin.site.register(Page)

### Unregsiter Clutter ###
from django.contrib.sites.models import Site
admin.site.unregister(Site)

from django.contrib.auth.models import Group
admin.site.unregister(Group)
