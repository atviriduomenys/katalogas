# Generated by Django 3.2.23 on 2024-01-24 03:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_requests', '0009_auto_20231105_1818'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='requestassignment',
            unique_together={('organization', 'request')},
        )
    ]