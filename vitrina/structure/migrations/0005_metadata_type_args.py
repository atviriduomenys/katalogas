# Generated by Django 3.2.16 on 2023-06-06 08:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_structure', '0004_alter_metadata_access'),
    ]

    operations = [
        migrations.AddField(
            model_name='metadata',
            name='type_args',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Tipo argumentai'),
        ),
    ]
