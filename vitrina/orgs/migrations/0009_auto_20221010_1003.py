# Generated by Django 3.2.16 on 2022-10-10 07:03

from django.db import migrations


def update_organization_representatives(apps, schema_editor):
    Organization = apps.get_model('vitrina_orgs', 'Organization')
    Representative = apps.get_model('vitrina_orgs', 'Representative')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for rep in Representative.objects.all():
        if rep.organization:
            rep.content_type = ContentType.objects.get_for_model(Organization)
            rep.object_id = rep.organization.pk
            rep.save()


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_orgs', '0008_auto_20221010_1001'),
        ('vitrina_requests', '0001_initial')
    ]

    operations = [
        migrations.RunPython(update_organization_representatives),
    ]
