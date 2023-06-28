# Generated by Django 3.2.19 on 2023-06-26 05:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_orgs', '0015_auto_20221205_1111'),
        ('vitrina_datasets', '0014_merge_0013_auto_20221202_0923_0013_auto_20221206_1003'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Kodinis pavadinimas')),
                ('uri', models.CharField(blank=True, max_length=255, verbose_name='Ryšio identifikatorius')),
                ('title', models.CharField(blank=True, max_length=255, verbose_name='Pavadinimas')),
            ],
            options={
                'db_table': 'attribution',
            },
        ),
        migrations.CreateModel(
            name='DatasetAttribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent', models.CharField(blank=True, max_length=255, null=True, verbose_name='Agentas')),
                ('attribution', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vitrina_datasets.attribution', verbose_name='Priskyrimo rūšis')),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vitrina_datasets.dataset', verbose_name='Duomenų rinkinys')),
                ('organization', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='vitrina_orgs.organization', verbose_name='Organizacija')),
            ],
            options={
                'db_table': 'dataset_attribution',
            },
        ),
    ]