# Generated by Django 3.2.16 on 2022-10-10 07:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_users', '0004_auto_20220909_1301'),
        ('vitrina_orgs', '0011_auto_20221012_1350'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),
    ]
