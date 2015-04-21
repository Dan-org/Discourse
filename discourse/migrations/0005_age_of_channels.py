# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
from uuid import uuid4
import uuidfield.fields
import yamlfield.fields


def translate_anchor(old_uri):
    parts = old_uri.split('/')
    if len(parts) == 3:
        return ".".join(parts), None
    elif len(parts) > 3:
        return ".".join(parts[:3]), "/".join(parts[3:])
    return old_uri, None


def migrate_comments_and_records(apps, schema_editor):
    Comment = apps.get_model("discourse", "Comment")
    Message = apps.get_model("discourse", "Message")
    Channel = apps.get_model("discourse", "Channel")
    Record = apps.get_model("discourse", "Record")
    Vote = apps.get_model("discourse", "Vote")

    mapping = {}
    channels = {}
    types = set()

    for record in Record.objects.all():
        anchor, rest = translate_anchor( record.anchor_uri )
        tags = []
        if rest:
            tags = ['sub-%s' % rest]

        if anchor in channels:
            channel = channels[anchor]
        else:
            channel = channels[anchor] = Channel.objects.create(id=anchor)

        if record.target_uri:
            tags.append(translate_anchor( record.target_uri )[0])

        types.add(record.predicate)

        m = Message.objects.create(
            uuid = uuid4().hex,
            type = record.predicate,
            channel = channel,
            author = record.actor,
            created = record.when,
            modified = record.when,
            deleted = None,
            tags = tags,
            content = record.data
        )

        mapping[record.id] = m

    comments = list( Comment.objects.all() )
    while comments:
        comment = comments.pop(0)
        if comment.parent_id and comment.parent_id not in mapping:
            comments.append(comment)
            continue

        anchor, rest = translate_anchor( comment.anchor_uri )
        tags = []
        if rest:
            tags = ['sub-%s' % rest]

        parent = None
        if comment.parent_id:
            parent = mapping[comment.parent_id]

        if anchor.startswith('discourse.event.'):
            continue

        if anchor.startswith('discourse.record.'):
            id = anchor.split('.')[-1]
            if not id in mapping:
                continue
            parent = mapping[id]
            channel = parent.channel
        else:
            if anchor in channels:
                channel = channels[anchor]
            else:
                channel = channels[anchor] = Channel.objects.create(id=anchor)

        m = Message.objects.create(
            uuid = uuid4().hex,
            type = 'reply' if parent else 'post',
            channel = channel,
            depth = 0 if not parent else parent.depth + 1,
            parent = parent,
            author = comment.author,

            created = comment.created,
            modified = comment.edited,
            deleted = comment.deleted,

            tags = ", ".join(tags),
            content = {'body': comment.body}
        )

        for vote in Vote.objects.filter(target_uri="discourse/comment/%s" % comment.id).select_related('user'):
            Message.objects.create(
                uuid = uuid4().hex,
                type = 'like',
                channel = channel,
                parent = m,
                author = vote.user,
                created = comment.created
            )

        mapping[comment.id] = m


class Migration(migrations.Migration):
    """
    This migration does a bunch of things.

    - Create channels, messages, and new attachments.
    - Move comments to message posts
    - Move votes to message likes
    - Move attachments to message attachments
    - Move records to messages
    """

    dependencies = [
        ('site', '0009_remove_user_digest_email'),
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
        migrations.RunPython(
            migrate_comments_and_records
        ),
        migrations.RemoveField(
            model_name='attachment',
            name='author',
        ),
        migrations.DeleteModel(
            name='Attachment',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='author',
        ),
        migrations.RemoveField(
            model_name='comment',
            name='parent',
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
        migrations.RemoveField(
            model_name='vote',
            name='user',
        ),
        migrations.DeleteModel(
            name='Vote',
        ),
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
    ]
