# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuidfield.fields
import yamlfield.fields
import uuid


def move_events_to_records(apps, schema_editor):
    Event = apps.get_model("discourse", "Event")
    Record = apps.get_model("discourse", "Record")
    events = [vars(e) for e in Event.objects.all()]
    for event in Event.objects.all():
        r = Record.objects.create(
            id = uuid.uuid4().hex,
            anchor_uri = event.path,
            predicate = event.type,
            when = event.created,
            actor =  event.actor,
            data = {},
        )
        r.when = event.created
        r.save()


def move_comment_votes_to_votes(apps, schema_editor):
    CommentVote = apps.get_model("discourse", "CommentVote")
    Vote = apps.get_model("discourse", "Vote")
    for cv in CommentVote.objects.all():
        uri = "discourse/comment/%s" % cv.comment_id
        Vote.objects.create(user=cv.user, target_uri=uri, value=cv.value)

def fix_attachments_filenames(apps, schema_editor):
    Attachment = apps.get_model("discourse", "Attachment")
    for a in Attachment.objects.all():
        app, model, pk, filename = a.anchor_uri.split('/', 4)
        a.filename = filename
        a.anchor_uri = "%s/%s/%s" % (app, model, pk)
        a.save()

def fix_comment_uris(apps, schema_editor):
    Comment = apps.get_model("discourse", "Comment")
    for c in Comment.objects.all():
        if ':' in c.anchor_uri:
            c.anchor_uri = c.anchor_uri.replace(':', '/')
            c.save()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('discourse', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name="Vote"
        ),
        migrations.CreateModel(
            name='Vote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('target_uri', models.CharField(max_length=255)),
                ('value', models.IntegerField()),
                ('user', models.ForeignKey(related_name=b'votes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RunPython(
            move_comment_votes_to_votes
        ),
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', uuidfield.fields.UUIDField(max_length=32, serialize=False, primary_key=True)),
                ('anchor_uri', models.CharField(max_length=255)),
                ('predicate', models.SlugField()),
                ('target_uri', models.CharField(max_length=255, null=True, blank=True)),
                ('when', models.DateTimeField(auto_now_add=True)),
                ('data', yamlfield.fields.YAMLField()),
                ('actor', models.ForeignKey(related_name=b'events_generated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-when'],
            },
            bases=(models.Model,),
        ),
        migrations.RunPython(
            move_events_to_records 
        ),
        migrations.RemoveField(
            model_name='attachmentzip',
            name='attachments',
        ),
        migrations.DeleteModel(
            name='AttachmentZip',
        ),
        migrations.RemoveField(
            model_name='commentvote',
            name='comment',
        ),
        migrations.RemoveField(
            model_name='commentvote',
            name='user',
        ),
        migrations.DeleteModel(
            name='CommentVote',
        ),
        migrations.RemoveField(
            model_name='event',
            name='actor',
        ),
        migrations.RemoveField(
            model_name='notice',
            name='events',
        ),
        migrations.RemoveField(
            model_name='notice',
            name='user',
        ),
        migrations.DeleteModel(
            name='Notice',
        ),
        migrations.AlterModelOptions(
            name='comment',
            options={'ordering': ('anchor_uri', '-value', 'id')},
        ),
        migrations.RenameField(
            model_name='attachment',
            old_name='path',
            new_name='anchor_uri',
        ),
        migrations.RenameField(
            model_name='attachment',
            old_name='mimetype',
            new_name='content_type',
        ),
        migrations.RenameField(
            model_name='comment',
            old_name='path',
            new_name='anchor_uri',
        ),
        migrations.RenameField(
            model_name='document',
            old_name='path',
            new_name='anchor_uri',
        ),
        migrations.RenameField(
            model_name='stream',
            old_name='path',
            new_name='anchor_uri',
        ),
        migrations.RenameField(
            model_name='subscription',
            old_name='path',
            new_name='target_uri',
        ),
        migrations.RemoveField(
            model_name='stream',
            name='events',
        ),
        migrations.DeleteModel(
            name='Event',
        ),
        migrations.AddField(
            model_name='attachment',
            name='filename',
            field=models.CharField(default='changeme', max_length=255),
            preserve_default=False,
        ),
        migrations.RunPython(
            fix_attachments_filenames
        ),
        migrations.AddField(
            model_name='stream',
            name='records',
            field=models.ManyToManyField(related_name=b'streams', to='discourse.Record'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='comment',
            name='value',
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='document',
            name='template',
            field=models.ForeignKey(blank=True, to='discourse.DocumentTemplate', null=True),
        ),
        migrations.RunPython(
            fix_comment_uris
        ),
    ]
