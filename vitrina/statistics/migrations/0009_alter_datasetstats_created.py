# Generated by Django 3.2.21 on 2023-09-20 09:24

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('statistics', '0008_alter_modeldownloadstats_created'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetstats',
            name='created',
            field=models.DateField(blank=True, default=datetime.datetime.today, null=True),
        ),
    ]