# Generated by Django 3.2.15 on 2022-10-04 06:43
from django.db import migrations, models
import django.db.models.deletion
import parler.fields
import parler.models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_datasets', '0006_remake_tags'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dataset',
            options={},
        ),
        migrations.RenameField(
            model_name='dataset',
            old_name='description',
            new_name='description_old'
        ),
        migrations.RenameField(
            model_name='dataset',
            old_name='title',
            new_name='title_old'
        ),
        migrations.RenameField(
            model_name='dataset',
            old_name='description_en',
            new_name='description_en_old'
        ),
        migrations.RenameField(
            model_name='dataset',
            old_name='title_en',
            new_name='title_en_old'
        ),
        migrations.CreateModel(
            name='DatasetTranslation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language_code', models.CharField(db_index=True, max_length=15, verbose_name='Language')),
                ('title', models.TextField(blank=True, verbose_name='Title')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('master', parler.fields.TranslationsForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='vitrina_datasets.dataset')),
            ],
            options={
                'verbose_name': 'Dataset Translation',
                'db_table': 'dataset_translation',
                'db_tablespace': '',
                'managed': True,
                'default_permissions': (),
                'unique_together': {('language_code', 'master')},
            },
            bases=(parler.models.TranslatedFieldsModel, models.Model),
        ),
    ]
