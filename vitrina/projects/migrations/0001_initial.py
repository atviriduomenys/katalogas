# Generated by Django 3.2.14 on 2022-09-01 09:38

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('value', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'application_setting',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ApplicationUseCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('author', models.CharField(blank=True, max_length=255, null=True)),
                ('beneficiary', models.CharField(blank=True, max_length=255, null=True)),
                ('platform', models.CharField(blank=True, max_length=255, null=True)),
                ('slug', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('status', models.CharField(blank=True, max_length=255, null=True)),
                ('url', models.CharField(blank=True, max_length=255, null=True)),
                ('uuid', models.CharField(blank=True, max_length=36, null=True, unique=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('imageuuid', models.CharField(blank=True, max_length=36, null=True)),
            ],
            options={
                'db_table': 'application_usecase',
                'managed': False,
            },
        ),
        migrations.AlterModelOptions(
            name='ApplicationUseCase',
            options={
                'db_table': 'application_usecase',
            }
        ),
        migrations.CreateModel(
            name='ApplicationUsecaseDatasetIds',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dataset_ids', models.BigIntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'application_usecase_dataset_ids',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PartnerApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('email', models.TextField(blank=True, null=True)),
                ('filename', models.TextField(blank=True, null=True)),
                ('letter', models.TextField(blank=True, null=True)),
                ('organization_title', models.TextField(blank=True, null=True)),
                ('phone', models.TextField(blank=True, null=True)),
                ('viisp_email', models.CharField(blank=True, max_length=255, null=True)),
                ('viisp_first_name', models.CharField(blank=True, max_length=255, null=True)),
                ('viisp_last_name', models.CharField(blank=True, max_length=255, null=True)),
                ('viisp_phone', models.CharField(blank=True, max_length=255, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('status', models.CharField(blank=True, max_length=255, null=True)),
                ('viisp_dob', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'partner_application',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField(default=1)),
                ('beneficiary_group', models.CharField(blank=True, max_length=255, null=True)),
                ('benefit', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('extra_information', models.TextField(blank=True, null=True)),
                ('slug', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('status', models.CharField(blank=True, max_length=255, null=True)),
                ('url', models.CharField(blank=True, max_length=255, null=True)),
                ('uuid', models.CharField(blank=True, max_length=36, null=True, unique=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('imageuuid', models.CharField(blank=True, max_length=36, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'usecase',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='UsecaseDatasetIds',
            fields=[
                ('dataset_ids', models.BigIntegerField(blank=True, null=True)),
                ('usecase', models.ForeignKey(on_delete=models.deletion.DO_NOTHING,
                                              to='vitrina_projects.Project'))
            ],
            options={
                'db_table': 'usecase_dataset_ids',
                'managed': False,
            },
        ),
        migrations.AlterModelOptions(
            name='UsecaseDatasetIds',
            options={
                'db_table': 'usecase_dataset_ids',
            }
        ),
        migrations.AddField(
            model_name='UsecaseDatasetIds',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.CreateModel(
            name='UsecaseLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('usecase_uuid', models.CharField(blank=True, max_length=255, null=True)),
                ('user_id', models.BigIntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'usecase_like',
                'managed': False,
            },
        ),
    ]
