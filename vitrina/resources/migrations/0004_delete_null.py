import mimetypes
from django.db import migrations, models
import django.db.models.deletion


def delete_resources_with_dataset_null(apps, schema_editor):
    DatasetDistribution = apps.get_model("vitrina_resources", "DatasetDistribution")

    for resource in DatasetDistribution.objects.all():
        if not resource.dataset:
            resource.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0003_alter_datasetdistribution_filename'),
    ]

    operations = [
        migrations.RunPython(delete_resources_with_dataset_null),
    ]