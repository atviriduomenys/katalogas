# Generated by Django 3.2.23 on 2023-11-21 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_structure', '0012_alter_metadata_title'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metadata',
            name='prepare',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Formulė'),
        ),
        migrations.AlterField(
            model_name='metadata',
            name='ref',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Ryšys'),
        ),
        migrations.AlterField(
            model_name='metadata',
            name='source',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Šaltinis'),
        ),
    ]