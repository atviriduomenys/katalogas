from django.db import migrations, models
import django.db.models.deletion
import uuid
import vitrina.validators


def copy_legacy_endpoint_descriptions(apps, schema_editor):
    Dataset = apps.get_model("vitrina_datasets", "Dataset")
    EndpointDescription = apps.get_model("vitrina_datasets", "EndpointDescription")

    for dataset in Dataset.objects.exclude(endpoint_description_deprecated__isnull=True).exclude(
        endpoint_description_deprecated=""
    ):
        url = dataset.endpoint_description_deprecated
        description, _ = EndpointDescription.objects.get_or_create(download_url=url)
        description.datasets.add(dataset)


def remove_endpoint_descriptions(apps, schema_editor):
    # The deprecated scalar column is left untouched; only the new model data is dropped.
    EndpointDescription = apps.get_model("vitrina_datasets", "EndpointDescription")
    EndpointDescription.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("vitrina_datasets", "0046_alter_dataset_endpoint_description_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EndpointDescription",
            fields=[
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, null=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, null=True),
                ),
                (
                    "download_url",
                    models.CharField(
                        max_length=512,
                        unique=True,
                        validators=[vitrina.validators.validate_absolute_uri],
                        verbose_name="API specifikacija",
                    ),
                ),
            ],
            options={
                "verbose_name": "API specifikacija",
                "verbose_name_plural": "API specifikacijos",
            },
        ),
        # Keep the existing physical column `endpoint_description` but rename the
        # model field to `endpoint_description_deprecated`. No database change.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name="dataset",
                    name="endpoint_description",
                ),
                migrations.AddField(
                    model_name="dataset",
                    name="endpoint_description_deprecated",
                    field=models.CharField(
                        blank=True,
                        db_column="endpoint_description",
                        max_length=512,
                        null=True,
                        validators=[vitrina.validators.validate_absolute_uri],
                        verbose_name="API specifikacija (pasenęs)",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="dataset",
            name="endpoint_description",
            field=models.ManyToManyField(
                blank=True,
                related_name="datasets",
                to="vitrina_datasets.endpointdescription",
                verbose_name="API specifikacija",
            ),
        ),
        migrations.RunPython(
            copy_legacy_endpoint_descriptions,
            reverse_code=remove_endpoint_descriptions,
        ),
    ]
