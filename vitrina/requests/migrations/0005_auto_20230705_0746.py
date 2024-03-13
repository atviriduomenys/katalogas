# Generated by Django 3.2.19 on 2023-07-05 04:46

from django.db import migrations, models
import django.db.models.deletion
from vitrina.datasets.models import Dataset
from django.core.exceptions import ObjectDoesNotExist



def migrate_request_datasets(apps, schema_editor):
    Request = apps.get_model('vitrina_requests', 'Request')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    for request in Request.objects.filter(dataset_id__isnull=False):
        request.content_type = ContentType.objects.get_for_model(Dataset)
        request.object_id = request.dataset_id
        try:
            dataset = Dataset.public.get(pk=request.dataset_id)
            request.dataset = dataset
        except ObjectDoesNotExist:
            request.dataset = None
        request.save()


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('vitrina_requests', '0004_auto_20230705_0746'),
        ('vitrina_datasets', '0017_merge_20230629_0914'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='request',
            options={'managed': True},
        ),
        migrations.AlterModelOptions(
            name='requestevent',
            options={'managed': True},
        ),
        migrations.AlterModelOptions(
            name='requeststructure',
            options={'managed': True},
        ),
        migrations.AddField(
            model_name='request',
            name='content_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='Objekto tipas'),
        ),
        migrations.AddField(
            model_name='request',
            name='external_content_type',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='request',
            name='external_object_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='request',
            name='object_id',
            field=models.PositiveIntegerField(null=True, verbose_name='Objekto id'),
        ),
        migrations.RunPython(migrate_request_datasets)
    ]
