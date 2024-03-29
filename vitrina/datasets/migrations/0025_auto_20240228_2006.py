# Generated by Django 3.2.24 on 2024-02-28 18:06

from django.db import migrations, models
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Representative
from django.contrib.admin.options import get_content_type_for_model
from reversion.models import Version




def fix_dataset_managers(apps, schema_editor):
    for dataset in Dataset.objects.all():
        dataset_reps = Representative.objects.filter(
            object_id=dataset.id,
            content_type=get_content_type_for_model(Dataset)
        )
        if not dataset_reps:
            created_event = Version.objects.get_for_object(dataset).first()
            if created_event and created_event.revision and created_event.revision.user:
                Representative.objects.create(
                    content_type=get_content_type_for_model(Dataset),
                    object_id=dataset.id,
                    user=created_event.revision.user,
                    email=created_event.revision.user.email,
                    role=Representative.COORDINATOR if created_event.revision.user.is_coordinator \
                        else Representative.MANAGER
                )


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_datasets', '0024_auto_20231204_1436'),
    ]

    operations = [
        migrations.RunPython(fix_dataset_managers),
    ]
