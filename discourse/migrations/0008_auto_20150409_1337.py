# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('discourse', '0007_auto_20150408_1853'),
    ]

    operations = [
        migrations.AddField(
            model_name='messagetag',
            name='type',
            field=models.SlugField(default=b'tag', max_length=24),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='messagetag',
            name='message',
            field=models.ForeignKey(related_name=b'tag_set', to='discourse.Message'),
        ),
    ]
