# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2018-01-14 13:18
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('map_app', '0002_auto_20180114_1315'),
    ]

    operations = [
        migrations.AlterField(
            model_name='centralsite',
            name='pub_date',
            field=models.DateTimeField(default=datetime.datetime(2018, 1, 14, 13, 18, 15, 611619, tzinfo=utc), verbose_name='date published'),
        ),
    ]
