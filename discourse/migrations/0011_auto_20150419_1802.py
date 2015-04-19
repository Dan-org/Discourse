# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuidfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('discourse', '0010_auto_20150419_1333'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='uuid',
            field=uuidfield.fields.UUIDField(serialize=False, primary_key=True),
        ),
    ]
