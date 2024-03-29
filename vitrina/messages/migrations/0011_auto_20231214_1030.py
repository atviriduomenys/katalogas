# Generated by Django 3.2.23 on 2023-12-14 08:30

from django.db import migrations


def delete_email_templates(apps, schema_editor):
    email_templates = apps.get_model('vitrina_messages', "EmailTemplate")
    for template in email_templates.objects.all():
        template.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_messages', '0010_auto_20231213_0943'),
    ]

    operations = [
        migrations.RunPython(delete_email_templates)
    ]
