# Generated by Django 3.2.19 on 2023-05-26 11:30

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Stats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('type', models.CharField(max_length=255)),
                ('model_id', models.BigIntegerField(blank=True, null=True)),
                ('model_source', models.CharField(blank=True, max_length=255, null=True)),
                ('model', models.CharField(blank=True, max_length=255, null=True)),
                ('model_format', models.CharField(blank=True, max_length=255, null=True)),
                ('model_requests', models.BigIntegerField(blank=True, null=True)),
                ('model_objects', models.BigIntegerField(blank=True, null=True)),
                ('model_field_count', models.BigIntegerField(blank=True, null=True)),
                ('dataset_id', models.BigIntegerField(blank=True, null=True)),
                ('dataset_models', models.BigIntegerField(blank=True, null=True)),
                ('dataset_distributions', models.BigIntegerField(blank=True, null=True)),
                ('datasets_total', models.BigIntegerField(blank=True, null=True)),
                ('dataset_requests', models.BigIntegerField(blank=True, null=True)),
                ('dataset_projects', models.BigIntegerField(blank=True, null=True)),
                ('dataset_maturity_level', models.BigIntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'statistic',
                'managed': True,
            },
        ),
    ]