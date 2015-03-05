# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('discourse', '0003_record_tags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='record',
            name='actor',
            field=models.ForeignKey(related_name=b'events_generated', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
