# Generated by Django 3.2.22 on 2023-11-10 11:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_structure', '0009_auto_20231108_0939'),
    ]

    operations = [
        migrations.AlterField(
            model_name='metadataversion',
            name='name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Vardas'),
        ),
        migrations.AlterField(
            model_name='metadataversion',
            name='prepare',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Formulė'),
        ),
        migrations.AlterField(
            model_name='metadataversion',
            name='ref',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Ryšys'),
        ),
        migrations.AlterField(
            model_name='metadataversion',
            name='source',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Šaltinis'),
        ),
        migrations.AlterField(
            model_name='metadataversion',
            name='type',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Tipas'),
        ),
    ]