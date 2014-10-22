# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import yamlfield.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(max_length=255)),
                ('mimetype', models.CharField(max_length=255)),
                ('caption', models.TextField(blank=True)),
                ('featured', models.BooleanField(default=False)),
                ('hidden', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('order', models.IntegerField(default=0)),
                ('file', models.FileField(null=True, upload_to=b'attachments', blank=True)),
                ('link', models.CharField(max_length=255, null=True, blank=True)),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AttachmentZip',
            fields=[
                ('hash', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('updated', models.DateTimeField(null=True, blank=True)),
                ('file', models.FileField(null=True, upload_to=b'attachment_zips', blank=True)),
                ('status', models.SlugField(default=b'working', choices=[(b'working', b'Working'), (b'ready', b'Ready'), (b'failed', b'Failed')])),
                ('attachments', models.ManyToManyField(to='discourse.Attachment', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('deleted', models.DateTimeField(null=True, blank=True)),
                ('edited', models.DateTimeField(null=True, blank=True)),
                ('value', models.IntegerField(default=0)),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('parent', models.ForeignKey(related_name=b'children', blank=True, to='discourse.Comment', null=True)),
            ],
            options={
                'ordering': ('path', '-value', 'id'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CommentVote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.IntegerField()),
                ('comment', models.ForeignKey(related_name=b'votes', to='discourse.Comment')),
                ('user', models.ForeignKey(related_name=b'comment_votes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(max_length=255)),
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
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.SlugField()),
                ('path', models.CharField(max_length=255)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(related_name=b'events_generated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Notice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('read', models.DateTimeField(null=True, blank=True)),
                ('events', models.ManyToManyField(to='discourse.Event')),
                ('user', models.ForeignKey(related_name=b'notices', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Stream',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(max_length=255)),
                ('events', models.ManyToManyField(related_name=b'streams', to='discourse.Event')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(max_length=255)),
                ('toggle', models.BooleanField(default=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(max_length=255)),
                ('value', models.IntegerField()),
                ('user', models.ForeignKey(related_name=b'votes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='document',
            name='template',
            field=models.ForeignKey(to='discourse.DocumentTemplate'),
            preserve_default=True,
        ),
    ]
