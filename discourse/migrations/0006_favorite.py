# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('discourse', '0005_auto_20150322_2124'),
    ]

    operations = [
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('subscription_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='discourse.Subscription')),
            ],
            options={
            },
            bases=('discourse.subscription',),
        ),
    ]
