from django.db import migrations


def migrate_creator_to_attribution(apps, schema_editor):
    Dataset = apps.get_model("vitrina_datasets", "Dataset")
    Attribution = apps.get_model("vitrina_datasets", "Attribution")
    DatasetAttribution = apps.get_model("vitrina_datasets", "DatasetAttribution")

    creator_attribution = Attribution.objects.filter(name="creator").first()
    if not creator_attribution:
        return

    for dataset in Dataset.objects.filter(information_system_creator__isnull=False):
        DatasetAttribution.objects.create(
            dataset=dataset,
            attribution=creator_attribution,
            organization_id=dataset.information_system_creator_id,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("vitrina_datasets", "0045_dataset_version_notes_datasetqualifiedrelation"),
    ]

    operations = [
        migrations.RunPython(migrate_creator_to_attribution, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="dataset",
            name="information_system_creator",
        ),
    ]
