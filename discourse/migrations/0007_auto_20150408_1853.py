# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('site', '0007_auto_20150408_1853'),
        ('discourse', '0006_favorite'),
    ]

    operations = [
        migrations.CreateModel(
            name='MessageTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField()),
                ('message', models.ForeignKey(related_name=b'tags', to='discourse.Message')),
            ],
            options={
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
        migrations.DeleteModel(
            name='Comment',
        ),
        migrations.RemoveField(
            model_name='old_attachments',
            name='author',
        ),
        migrations.DeleteModel(
            name='old_attachments',
        ),
        migrations.RemoveField(
            model_name='vote',
            name='user',
        ),
        migrations.DeleteModel(
            name='Vote',
        ),
        migrations.RemoveField(
            model_name='message',
            name='tags',
        ),
    ]
