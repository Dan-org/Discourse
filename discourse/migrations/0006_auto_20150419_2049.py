# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuidfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('discourse', '0005_auto_20150419_1937'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('uuid', uuidfield.fields.UUIDField(primary_key=True, auto=True, serialize=False)),
                ('mimetype', models.CharField(max_length=255)),
                ('filename', models.CharField(max_length=255)),
                ('source', models.FileField(upload_to=b'attachments')),
                ('message', models.ForeignKey(related_name=b'attachments', to='discourse.Message')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        #migrations.CreateModel(
        #    name='Favorite',
        #    fields=[
        #        ('subscription_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='discourse.Subscription')),
        #    ],
        #    options={
        #    },
        #    bases=('discourse.subscription',),
        #),
        #migrations.DeleteModel(
        #    name='Comment',
        #),
        #migrations.DeleteModel(
        #    name='Vote',
        #),
    ]
