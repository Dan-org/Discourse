# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def fix_tags(apps, schema_editor):
    MessageTag = apps.get_model("discourse", "MessageTag")
    Message = apps.get_model("discourse", "Message")

    for message in Message.objects.all():
        tags = [x.slug for x in message.tag_set.all()]
        message.tags = " ".join(tags)
        message.save()


class Migration(migrations.Migration):
    dependencies = [
        ('discourse', '0009_auto_20150417_1741'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='tags',
            field=models.TextField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='message',
            name='keys',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.RunPython(
            fix_tags
        ),
        migrations.DeleteModel(
            name='MessageTag',
        ),
    ]
