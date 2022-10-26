# Generated by Django 3.2.16 on 2022-10-10 07:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('vitrina_orgs', '0007_auto_20220928_1451'),
    ]

    operations = [
        migrations.AddField(
            model_name='representative',
            name='content_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='representative',
            name='object_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]