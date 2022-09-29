# Generated by Django 3.2.15 on 2022-09-29 09:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_orgs', '0004_auto_20220929_1227'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vitrina_datasets', '0003_auto_20220905_0914'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatasetMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('creator', 'Creator'), ('contributor', 'Contributor'), ('publisher', 'Publisher')], max_length=255)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('contact', models.BooleanField(default=False)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vitrina_datasets.dataset')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vitrina_orgs.organization')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
