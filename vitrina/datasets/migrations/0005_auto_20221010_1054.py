# Generated by Django 3.2.16 on 2022-10-10 07:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_datasets', '0004_alter_dataset_options'),
        ('vitrina_orgs', '0011_auto_20221012_1350'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataset',
            name='coordinator',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='manager',
        ),
        migrations.RemoveField(
            model_name='dataset',
            name='representative_id',
        ),
    ]
