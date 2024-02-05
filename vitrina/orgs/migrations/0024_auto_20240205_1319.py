# Generated by Django 3.2.23 on 2024-02-05 11:19

from django.db import migrations
from django.db.models import Q


def remove_disabled_representatives(apps, schema_editor):
    Representative = apps.get_model('vitrina_orgs', 'Representative')

    Representative.objects.filter(
        Q(user__disabled=True) |
        Q(user__suspended=True)
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_orgs', '0023_auto_20231221_1041'),
    ]

    operations = [
        migrations.RunPython(remove_disabled_representatives)
    ]
