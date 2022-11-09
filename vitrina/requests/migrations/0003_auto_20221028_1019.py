# Generated by Django 3.2.16 on 2022-10-28 07:19

from django.db import migrations


def fix_request_statuses(apps, schema_editor):
    Request = apps.get_model('vitrina_requests', 'Request')

    for request in Request.objects.all():
        if request.status == "ALREADY_OPENED":
            request.status = "OPENED"
            request.save(update_fields=['status'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_requests', '0002_auto_20221010_1418'),
    ]

    operations = [
        migrations.RunPython(fix_request_statuses)
    ]