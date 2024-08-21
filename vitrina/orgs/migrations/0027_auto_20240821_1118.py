# Generated by Django 3.2.25 on 2024-08-21 08:18

from django.db import migrations, models


def update_representative_request_status(apps, schema_editor):
    RepresentativeRequest = apps.get_model('vitrina_orgs', 'RepresentativeRequest')
    Representative = apps.get_model('vitrina_orgs', 'Representative')
    Organization = apps.get_model('vitrina_orgs', 'Organization')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    for request in RepresentativeRequest.objects.all():
        if Representative.objects.filter(
            user=request.user,
            content_type=ContentType.objects.get_for_model(Organization),
            object_id=request.organization_id
        ).exists():
            request.status = "APPROVED"
        else:
            request.status = "CREATED"
        request.save(update_fields=["status"])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_orgs', '0026_auto_20240821_1000'),
    ]

    operations = [
        migrations.AlterField(
            model_name='representativerequest',
            name='status',
            field=models.CharField(blank=True, choices=[('REJECTED', 'Atmestas'), ('APPROVED', 'Patvirtintas'), ('CREATED', 'Pateiktas')], default='CREATED', max_length=255, null=True, verbose_name='Būsena'),
        ),
        migrations.RunPython(update_representative_request_status),
    ]
