# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuidfield.fields
import yamlfield.fields

from uuid import uuid4

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('discourse', '0004_auto_20150226_1509'),
    ]

    operations = [
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255, null=True, blank=True)),
                ('tags', models.TextField(blank=True)),
                ('keys', models.TextField(blank=True)),
                ('publish_keys', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(related_name=b'channels', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
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
        migrations.CreateModel(
            name='Message',
            fields=[
                ('uuid', uuidfield.fields.UUIDField(serialize=False, primary_key=True)),
                ('type', models.SlugField(max_length=255)),
                ('order', models.IntegerField(default=0)),
                ('depth', models.IntegerField(default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('deleted', models.DateTimeField(null=True, blank=True)),
                ('tags', models.TextField(null=True, blank=True)),
                ('keys', models.TextField(null=True, blank=True)),
                ('content', yamlfield.fields.YAMLField(null=True, blank=True)),
                ('value', models.IntegerField(default=0)),
                ('author', models.ForeignKey(related_name=b'messages', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('channel', models.ForeignKey(related_name=b'messages', to='discourse.Channel')),
                ('parent', models.ForeignKey(related_name=b'children', blank=True, to='discourse.Message', null=True)),
            ],
            options={
                'ordering': ['depth', 'parent_id', 'order', '-created'],
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='comment',
            name='author',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='parent',
        ),
        migrations.RemoveField(
            model_name='vote',
            name='user',
        ),
        migrations.RemoveField(
            model_name='attachment',
            name='author',
        ),
        migrations.RemoveField(
            model_name='attachment',
            name='id',
        ),
        migrations.DeleteModel(
            name='attachment'
        )
    ]