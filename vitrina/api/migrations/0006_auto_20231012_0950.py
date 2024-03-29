# Generated by Django 3.2.22 on 2023-10-12 06:50

from django.db import migrations

from vitrina.orgs.services import hash_api_key


def hash_api_keys(apps, schema_editor):
    ApiKey = apps.get_model('vitrina_api', 'ApiKey')

    for obj in ApiKey.objects.exclude(
        api_key__startswith="DUPLICATE"
    ):
        obj.api_key = hash_api_key(obj.api_key)
        obj.save(update_fields=['api_key'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_api', '0005_restore_old_icons'),
    ]

    operations = [
        migrations.RunPython(hash_api_keys)
    ]
