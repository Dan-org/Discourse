# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuidfield.fields
import yamlfield.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('uuid', uuidfield.fields.UUIDField(serialize=False, primary_key=True)),
                ('mimetype', models.CharField(max_length=255)),
                ('filename', models.CharField(max_length=255)),
                ('source', models.FileField(upload_to=b'attachments')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
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
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('anchor_uri', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DocumentContent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('attribute', models.SlugField()),
                ('body', models.TextField()),
                ('document', models.ForeignKey(related_name=b'content', to='discourse.Document')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DocumentTemplate',
            fields=[
                ('slug', models.SlugField(serialize=False, primary_key=True)),
                ('structure', yamlfield.fields.YAMLField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('uuid', uuidfield.fields.UUIDField(serialize=False, primary_key=True)),
                ('type', models.SlugField(max_length=255)),
                ('order', models.IntegerField(default=0)),
                ('depth', models.IntegerField(default=0)),
                ('created', models.DateTimeField()),
                ('modified', models.DateTimeField(null=True, blank=True)),
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
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('target_uri', models.CharField(max_length=255)),
                ('toggle', models.BooleanField(default=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('subscription_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='discourse.Subscription')),
            ],
            options={
            },
            bases=('discourse.subscription',),
        ),
        migrations.AddField(
            model_name='subscription',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='document',
            name='template',
            field=models.ForeignKey(blank=True, to='discourse.DocumentTemplate', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='attachment',
            name='message',
            field=models.ForeignKey(related_name=b'attachments', to='discourse.Message'),
            preserve_default=True,
        ),
    ]
