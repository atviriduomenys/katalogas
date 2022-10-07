from django.db import migrations, models


def remake_region_and_municipality(apps, schema_editor):
    DatasetDistribution = apps.get_model("vitrina_resources", "DatasetDistribution")

    for resource in DatasetDistribution.objects.all():
        if resource.region and not resource.municipality:
            resource.geo_location = resource.region
        elif not resource.region and resource.municipality:
            resource.geo_location = resource.municipality
        elif resource.region and resource.municipality:
            resource.geo_location = str(resource.region + " " + resource.municipality)
        else:
            resource.geo_location = ''
        resource.save(update_fields=['geo_location'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0005_generate_mimetypes'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetdistribution',
            name='geo_location',
            field=models.CharField(blank=True, max_length=255, verbose_name='Geografinė aprėptis'),
        ),
        migrations.RunPython(remake_region_and_municipality),
        migrations.RemoveField(
            model_name='datasetdistribution',
            name='region',
        ),
        migrations.RemoveField(
            model_name='datasetdistribution',
            name='municipality',
        ),
    ]