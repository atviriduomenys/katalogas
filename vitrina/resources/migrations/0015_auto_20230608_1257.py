# Generated by Django 3.2.16 on 2023-06-08 09:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0014_fix_dates'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='format',
            options={},
        ),
        migrations.AlterField(
            model_name='format',
            name='title',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
    ]
