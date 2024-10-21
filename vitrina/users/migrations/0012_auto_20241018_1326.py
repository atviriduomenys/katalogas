# Generated by Django 3.2.25 on 2024-10-18 10:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_users', '0011_auto_20240917_0926'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oldpassword',
            name='password',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='failed_login_attempts',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='user',
            name='status',
            field=models.CharField(blank=True,
                                   choices=[('active', 'Aktyvus'), ('awaiting_confirmation', 'Laukiama patvirtinimo'),
                                            ('suspended', 'Suspenduotas'), ('deleted', 'Pašalintas'),
                                            ('locked', 'Užrakintas')], default='awaiting_confirmation', max_length=255,
                                   null=True),
        ),
    ]
