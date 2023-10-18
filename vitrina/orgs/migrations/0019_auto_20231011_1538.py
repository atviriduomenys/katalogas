# Generated by Django 3.2.21 on 2023-10-11 12:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vitrina_orgs', '0018_auto_20230925_0843'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='kind',
            field=models.CharField(choices=[('com', 'Verslo organizacija'), ('gov', 'Valstybinė įstaiga'), ('org', 'Nepelno ir nevalstybinė organizacija')], default='org', max_length=36, verbose_name='Tipas'),
        ),
        migrations.AlterField(
            model_name='representative',
            name='role',
            field=models.CharField(choices=[('coordinator', 'Koordinatorius'), ('manager', 'Tvarkytojas')], max_length=255),
        ),
        migrations.CreateModel(
            name='RepresentativeRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document', models.FileField(upload_to='')),
                ('org_code', models.CharField(blank=True, max_length=255, null=True)),
                ('org_name', models.CharField(blank=True, max_length=255, null=True)),
                ('org_slug', models.CharField(blank=True, max_length=255, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'representative_request',
                'managed': True,
            },
        ),
    ]
