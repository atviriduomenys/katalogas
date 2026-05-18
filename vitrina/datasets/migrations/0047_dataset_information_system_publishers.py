from django.db import migrations, models


def migrate_publisher_to_m2m(apps, schema_editor):
    Dataset = apps.get_model("vitrina_datasets", "Dataset")
    for dataset in Dataset.objects.filter(information_system_publisher__isnull=False):
        dataset.information_system_publishers.add(dataset.information_system_publisher_id)


class Migration(migrations.Migration):

    dependencies = [
        ("vitrina_datasets", "0046_remove_dataset_information_system_creator"),
        ("vitrina_orgs", "0005_delete_agent"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataset",
            name="information_system_publishers",
            field=models.ManyToManyField(
                blank=True,
                related_name="information_system_publisher_datasets",
                to="vitrina_orgs.organization",
                verbose_name="Informacinės sistemos tvarkytojai",
                help_text="Ši savybė nurodo subjektus (organizacijas), atsakingas už IS prieinamumą. Atitinka dct:publisher"
            ),
        ),
        migrations.RunPython(migrate_publisher_to_m2m, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="dataset",
            name="information_system_publisher",
        ),
    ]
