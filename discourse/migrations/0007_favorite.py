# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('discourse', '0006_migrate_documents'),
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
