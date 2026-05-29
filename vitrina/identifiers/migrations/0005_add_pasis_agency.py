from django.db import migrations


def create_pasis_agency(apps, schema_editor):
    Agency = apps.get_model("vitrina_identifiers", "Agency")

    agency, created = Agency.objects.get_or_create(
        code="pasis",
        defaults={
            "name": "Paslaugų ir gaminių informacinė sistema",
            "uri": "https://www.pasis.lt",
            "identifier_validation_type": None,
        },
    )
    if not created:
        agency.identifier_validation_type = None
        agency.save()


class Migration(migrations.Migration):

    dependencies = [
        ("vitrina_identifiers", "0004_auto_20250825_1001"),
    ]

    operations = [
        migrations.RunPython(create_pasis_agency, reverse_code=migrations.RunPython.noop),
    ]
