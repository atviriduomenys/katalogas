import mimetypes
from django.db import migrations, models


def generate_mimetype_for_format_table(apps, schema_editor):
    formats = {'csv': 'text/csv',
               'rdf': 'Application/rdf+xml',
               'pdf': 'application/pdf',
               'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
               'json': 'application/json',
               'xml': 'application/xml',
               'shape': 'application/octet-stream',
               'api': 'application/vnd.api+json',
               'url': 'text/url',
               'doc': 'application/msword',
               'html': 'text/html'}
    Format = apps.get_model("vitrina_resources", "Format")

    for format in Format.objects.all():
        mimetype = formats[str(format.extension).lower()]
        format.mimetype = mimetype
        format.save(update_fields=['mimetype'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0004_delete_null'),
    ]

    operations = [
        migrations.RunPython(generate_mimetype_for_format_table),
    ]