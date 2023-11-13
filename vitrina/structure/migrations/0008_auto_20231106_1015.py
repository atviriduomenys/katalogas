# Generated by Django 3.2.22 on 2023-11-06 08:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_datasets', '0021_auto_20230919_0905'),
        ('vitrina_structure', '0007_auto_20230919_1011'),
    ]

    operations = [
        migrations.AddField(
            model_name='metadata',
            name='draft',
            field=models.BooleanField(default=True, verbose_name='Priskirta versijai'),
        ),
        migrations.CreateModel(
            name='Version',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.IntegerField(blank=True, null=True, verbose_name='Versija')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Sukūrimo data')),
                ('released', models.DateField(blank=True, null=True, verbose_name='Išleidimo data')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Aprašymas')),
                ('deployed', models.DateTimeField(blank=True, null=True, verbose_name='Įkėlimo į saugyklą data')),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='dataset_version', to='vitrina_datasets.dataset', verbose_name='Duomenų rinkinys')),
            ],
            options={
                'verbose_name': 'Versija',
                'db_table': 'version',
                'unique_together': {('dataset', 'version')},
            },
        ),
        migrations.AddField(
            model_name='metadata',
            name='metadata_version',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='vitrina_structure.version', verbose_name='Versija'),
        ),
        migrations.CreateModel(
            name='MetadataVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metadata', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vitrina_structure.metadata', verbose_name='Metaduomenys')),
                ('version', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vitrina_structure.version', verbose_name='Versija')),
            ],
            options={
                'verbose_name': 'Metaduomenų versija',
                'db_table': 'metadata_version',
                'unique_together': {('metadata', 'version')},
            },
        ),
    ]