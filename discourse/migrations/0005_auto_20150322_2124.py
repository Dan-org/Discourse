# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuidfield.fields
import yamlfield.fields


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
                ('owner', models.ForeignKey(related_name=b'channels', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', uuidfield.fields.UUIDField(auto=True)),
                ('type', models.SlugField(max_length=255)),
                ('channel', models.ForeignKey(related_name=b'messages', to='discourse.Channel')),
                ('order', models.IntegerField(default=0)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('deleted', models.DateTimeField(null=True, blank=True)),
                ('tags', models.CharField(max_length=255, null=True, blank=True)),
                ('keys', models.CharField(max_length=255, null=True, blank=True)),
                ('content', yamlfield.fields.YAMLField(null=True, blank=True)),
                ('value', models.IntegerField(default=0)),
                ('author', models.ForeignKey(related_name=b'messages', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('parent', models.ForeignKey(related_name=b'children', blank=True, to='discourse.Message', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RenameModel(
            old_name='attachment',
            new_name='old_attachments',
        ),
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('uuid', uuidfield.fields.UUIDField(auto=True, primary_key=True)),
                ('mimetype', models.CharField(max_length=255)),
                ('filename', models.CharField(max_length=255)),
                ('source', models.FileField(upload_to=b'attachments')),
                ('message', models.ForeignKey(to='discourse.Message')),
            ],
            options={
            },
            bases=(models.Model,),
        )
    ]
