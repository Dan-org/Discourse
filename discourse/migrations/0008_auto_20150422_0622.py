# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuidfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('discourse', '0007_favorite'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='uuid',
            field=uuidfield.fields.UUIDField(serialize=False, primary_key=True),
        ),
    ]
