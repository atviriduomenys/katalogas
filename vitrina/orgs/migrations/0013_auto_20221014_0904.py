# Generated by Django 3.2.16 on 2022-10-14 06:04

from django.db import migrations


def fix_representative_roles(apps, shema_editor):
    Representative = apps.get_model('vitrina_orgs', 'Representative')
    for rep in Representative.objects.all():
        if rep.role == "orgcoordinator":
            rep.role = "coordinator"
        if rep.role == "orgrepresentative":
            rep.role = "manager"
        rep.save(update_fields=["role"])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_orgs', '0012_auto_20221012_1402'),
    ]

    operations = [
        migrations.RunPython(fix_representative_roles)
    ]
