# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def fix_child_depths(message):
    for child in message.children.all():
        child.depth = message.depth + 1
        child.save()
        fix_child_depths(child)


def fix_depths(apps, schema_editor):
    Message = apps.get_model("discourse", "Message")
    for m in Message.objects.filter(parent=None):
        fix_child_depths(m)


class Migration(migrations.Migration):

    dependencies = [
        ('discourse', '0008_auto_20150409_1337'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='message',
            options={'ordering': ['depth', 'parent_id', 'order', '-created']},
        ),
        migrations.AddField(
            model_name='message',
            name='depth',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.RunPython(
            fix_depths
        ),
    ]
