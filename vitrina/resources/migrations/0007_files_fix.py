import mimetypes
from django.db import migrations, models
import django.db.models.deletion


def fix_type_field_for_files(apps, schema_editor):
    DatasetDistribution = apps.get_model("vitrina_resources", "DatasetDistribution")
    Format = apps.get_model("vitrina_resources", "Format")

    for resource in DatasetDistribution.objects.all():
        if resource.file:
            mime_type = mimetypes.guess_type(str(resource.file))
            detected_format = Format.objects.filter(mimetype=mime_type).first()
            resource.format = detected_format
        if resource.type == 'URL':
            url_format = Format.objects.filter(extension='URL').first()
            resource.format = url_format
        resource.save(update_fields=['format'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0006_region_municipality'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetdistribution',
            name='filename',
            field=models.FileField(blank=True,
                                   help_text='Atvirų duomenų katalogas nėra skirtas duomenų talpinimui'
                                             ' ir įprastinių atveju duomenys turėtu būti talpinami'
                                             ' atvirų duomenų Saugykloje ar kitoje vietoje, pateikiant'
                                             ' tiesioginę duomenų atsisiuntimo nuorodą. Tačiau nedidelės'
                                             ' apimties (iki 5Mb) duomenų failus, galima talpinti ir kataloge.',
                                   max_length=255, null=True, upload_to='data/', verbose_name='Duomenų failas'),
        ),
        migrations.RenameField(
            model_name='datasetdistribution',
            old_name='filename',
            new_name='file',
        ),
        migrations.AlterField(
            model_name='datasetdistribution',
            name='url_format',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='vitrina_resources.format', verbose_name='Šaltinio formatas'),
        ),
        migrations.RenameField(
            model_name='datasetdistribution',
            old_name='url_format',
            new_name='format',
        ),
        migrations.RunPython(fix_type_field_for_files)
    ]
