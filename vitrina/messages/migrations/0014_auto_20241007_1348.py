# Generated by Django 3.2.25 on 2024-10-07 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_messages', '0013_auto_20240219_1254'),
    ]

    operations = [
        migrations.AddField(
            model_name='sentmail',
            name='identifier',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Identifikatorius'),
        ),
    ]
