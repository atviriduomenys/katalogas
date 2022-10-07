import mimetypes
from django.db import migrations, models


def generate_mimetype_for_format_table(apps, schema_editor):
    Format = apps.get_model("vitrina_resources", "Format")

    for format in Format.objects.all():
        mimetype = mimetypes.guess_type('file.' + format.extension)
        format.mimetype = mimetype
        format.save(update_fields=['mimetype'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0004_delete_null'),
    ]

    operations = [
        migrations.RunPython(generate_mimetype_for_format_table),
    ]