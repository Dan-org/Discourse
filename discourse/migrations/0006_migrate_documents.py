# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def migrate_documents(apps, schema_editor):
    Document = apps.get_model("discourse", "Document")
    for d in Document.objects.all():
        parts = d.anchor_uri.split('/')
        if len(parts) > 3:
            d.anchor_uri = ".".join(parts[:3]) + "/" + "/".join( parts[3:] )
        else:
            d.anchor_uri = ".".join(parts)
        d.save()


class Migration(migrations.Migration):

    dependencies = [
        ('discourse', '0005_age_of_channels'),
    ]

    operations = [
        migrations.RunPython(
            migrate_documents
        )
    ]
