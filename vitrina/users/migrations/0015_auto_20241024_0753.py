# Generated by Django 3.2.25 on 2024-10-24 04:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_users', '0014_merge_0012_auto_20241018_1326_0013_auto_20241023_1321'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='useremaildevice',
            options={'managed': True},
        ),
        migrations.AddField(
            model_name='useremaildevice',
            name='user_agent',
            field=models.TextField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='useremaildevice',
            name='ip_address',
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=40, null=True, verbose_name='IP adresas'),
        ),
    ]
