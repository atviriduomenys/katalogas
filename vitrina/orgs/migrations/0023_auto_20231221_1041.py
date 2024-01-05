# Generated by Django 3.2.23 on 2023-12-21 08:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vitrina_orgs', '0022_auto_20231212_2033'),
    ]

    operations = [
        migrations.AlterField(
            model_name='representativerequest',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vitrina_orgs.organization'),
        ),
        migrations.AlterField(
            model_name='representativerequest',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]