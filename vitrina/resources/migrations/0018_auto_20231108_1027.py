# Generated by Django 3.2.22 on 2023-11-08 08:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0017_merge_0016_auto_20230629_1124_0016_auto_20230711_0812'),
    ]

    operations = [
        migrations.AddField(
            model_name='format',
            name='media_type_uri',
            field=models.CharField(blank=True, max_length=255, verbose_name='Nuoroda į kontroliuojamą žodyną'),
        ),
        migrations.AddField(
            model_name='format',
            name='uri',
            field=models.CharField(blank=True, max_length=255, verbose_name='Nuoroda į kontroliuojamą žodyną'),
        ),
    ]
