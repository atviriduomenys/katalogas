# Generated by Django 3.2.23 on 2023-11-20 13:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_datasets', '0022_auto_20231110_1704'),
        ('vitrina_api', '0007_auto_20231116_1613'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apiscope',
            name='dataset',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vitrina_datasets.dataset', verbose_name='Duomenų rinkinys'),
        ),
    ]
