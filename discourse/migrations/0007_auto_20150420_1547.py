# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('discourse', '0006_auto_20150419_2049'),
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
        migrations.DeleteModel(
            name='Comment',
        ),
        migrations.RemoveField(
            model_name='record',
            name='actor',
        ),
        migrations.RemoveField(
            model_name='record',
            name='tags',
        ),
        migrations.RemoveField(
            model_name='stream',
            name='records',
        ),
        migrations.DeleteModel(
            name='Record',
        ),
        migrations.DeleteModel(
            name='Stream',
        ),
        migrations.DeleteModel(
            name='Vote',
        ),
    ]
