from django.db import migrations, models
import django.db.models.deletion


def remake_region_and_municipality(apps, schema_editor):
    DatasetDistribution = apps.get_model("vitrina_resources", "DatasetDistribution")
    Region = apps.get_model("vitrina_orgs", "Region")
    Municipality = apps.get_model("vitrina_orgs", "Municipality")

    for resource in DatasetDistribution.objects.all():
        if resource.region_old:
            region = Region.objects.filter(title=resource.region_old).first()
            resource.region = region
        if resource.municipality_old:
            municipality = Municipality.objects.filter(title=resource.municipality_old).first()
            resource.municipality = municipality
        resource.save(update_fields=['region', 'municipality'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0005_generate_mimetypes'),
    ]

    operations = [
        migrations.RenameField(
            model_name='datasetdistribution',
            old_name='region',
            new_name='region_old',
        ),
        migrations.RenameField(
            model_name='datasetdistribution',
            old_name='municipality',
            new_name='municipality_old',
        ),
        migrations.AddField(
            model_name='datasetdistribution',
            name='municipality',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='vitrina_orgs.municipality', verbose_name='Savivaldybė'),
        ),
        migrations.AddField(
            model_name='datasetdistribution',
            name='region',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='vitrina_orgs.region', verbose_name='Regionas'),
        ),
        migrations.RunPython(remake_region_and_municipality),
        migrations.RemoveField(
            model_name='datasetdistribution',
            name='region_old',
        ),
        migrations.RemoveField(
            model_name='datasetdistribution',
            name='municipality_old',
        ),
    ]