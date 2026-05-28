from django.db import migrations


def create_relates_to_data_service_relation(apps, schema_editor):
    Relation = apps.get_model("vitrina_datasets", "Relation")

    relation, created = Relation.objects.get_or_create(
        name="relatesToDataService",
        defaults={"uri": "dcataplt:relatesToDataService"},
    )

    relation.set_current_language("lt")
    relation.title = "Susijusi duomenų paslauga"
    relation.inversive_title = "Susijusi informacinė sistema"
    relation.save()

    relation.set_current_language("en")
    relation.title = "Relates to data service"
    relation.inversive_title = "Related information system"
    relation.save()


class Migration(migrations.Migration):

    dependencies = [
        ("vitrina_datasets", "0051_alter_dataset_access_rights"),
    ]

    operations = [
        migrations.RunPython(
            create_relates_to_data_service_relation,
            reverse_code=migrations.RunPython.noop,
        ),
    ]