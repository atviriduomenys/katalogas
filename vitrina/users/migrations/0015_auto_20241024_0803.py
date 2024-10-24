# Generated by Django 3.2.25 on 2024-10-24 05:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from vitrina.users.models import User

def set_password_last_updated_to_null(apps, schema_editor):
    User.objects.update(password_last_updated=None)

class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_users', '0014_merge_0012_auto_20241018_1326_0013_auto_20241023_1321'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='password_last_updated',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.RunPython(set_password_last_updated_to_null),
    ]
