# Generated by Django 3.2.19 on 2023-08-03 02:07

from django.db import migrations, models
import django.db.models.deletion

def copy_orgs(apps, schema_editor):
    Request = apps.get_model('vitrina_requests', 'Request')

    for request in Request.objects.filter(organization__isnull=False):
        request.organizations.add(request.organization)
        request.save()




class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_requests', '0006_auto_20230720_1648'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='organizations',
            field=models.ManyToManyField(to='vitrina_orgs.Organization'),
        ),
        migrations.RunPython(copy_orgs),
        migrations.RemoveField(
            model_name='request',
            name='organization',
        ),
    ]
