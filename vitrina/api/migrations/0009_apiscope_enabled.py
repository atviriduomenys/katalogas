# Generated by Django 3.2.23 on 2023-11-21 13:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_api', '0008_alter_apiscope_dataset'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiscope',
            name='enabled',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
