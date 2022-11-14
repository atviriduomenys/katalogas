# Generated by Django 3.2.16 on 2022-11-14 11:47
from datetime import datetime

from django.db import migrations, models


def fix_dates(apps, schema_editor):
    Dist = apps.get_model("vitrina_resources", "DatasetDistribution")

    for dist in Dist.objects.all():
        if dist.period_start in ('-', '', None):
            dist.period_start = None
        else:
            dist.period_start = datetime.strptime(str(dist.period_start), "%Y-%m-%d").date()
        if dist.period_end in ('-', '', None):
            dist.period_end = None
        else:
            dist.period_end = datetime.strptime(str(dist.period_end), "%Y-%m-%d").date()
        dist.save(update_fields=['period_start', 'period_end'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0012_alter_title_description'),
    ]

    operations = [
        migrations.RunPython(fix_dates),
        migrations.AlterField(
            model_name='datasetdistribution',
            name='period_end',
            field=models.DateField(blank=True, null=True, verbose_name='Periodo pabaiga'),
        ),
        migrations.AlterField(
            model_name='datasetdistribution',
            name='period_start',
            field=models.DateField(blank=True, null=True, verbose_name='Periodo pradžia'),
        ),
    ]
