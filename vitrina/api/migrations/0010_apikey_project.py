# Generated by Django 3.2.23 on 2023-12-04 11:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_projects', '0007_auto_20221205_1101'),
        ('vitrina_api', '0009_apiscope_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='apikey',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vitrina_projects.project'),
        ),
    ]
