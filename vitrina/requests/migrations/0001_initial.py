# Generated by Django 3.2.15 on 2022-10-04 07:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('vitrina_orgs', '0007_auto_20220928_1451'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Request',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField(default=1)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('dataset_id', models.BigIntegerField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('format', models.CharField(blank=True, max_length=255, null=True)),
                ('is_existing', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('periodicity', models.CharField(blank=True, max_length=255, null=True)),
                ('planned_opening_date', models.DateField(blank=True, null=True)),
                ('purpose', models.CharField(blank=True, max_length=255, null=True)),
                ('slug', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('status', models.CharField(blank=True, choices=[('CREATED', 'Pateiktas'), ('REJECTED', 'Atmestas'), ('OPENED', 'Atvertas'), ('ANSWERED', 'Atsakytas')], max_length=255, null=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('uuid', models.CharField(blank=True, max_length=36, null=True, unique=True)),
                ('changes', models.CharField(blank=True, max_length=255, null=True)),
                ('is_public', models.BooleanField(default=True)),
                ('structure_data', models.TextField(blank=True, null=True)),
                ('structure_filename', models.CharField(blank=True, max_length=255, null=True)),
                ('organization', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_orgs.organization')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'request',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='RequestStructure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('data_notes', models.CharField(blank=True, max_length=255, null=True)),
                ('data_title', models.CharField(blank=True, max_length=255, null=True)),
                ('data_type', models.CharField(blank=True, max_length=255, null=True)),
                ('dictionary_title', models.CharField(blank=True, max_length=255, null=True)),
                ('request_id', models.BigIntegerField(blank=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'request_structure',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='RequestEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('comment', models.TextField(blank=True, null=True)),
                ('meta', models.TextField(blank=True, null=True)),
                ('type', models.CharField(blank=True, max_length=255, null=True)),
                ('request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_requests.request')),
            ],
            options={
                'db_table': 'request_event',
                'managed': False,
            },
        ),
    ]
