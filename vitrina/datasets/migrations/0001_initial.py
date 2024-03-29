# Generated by Django 3.2.15 on 2022-09-20 06:58
import parler
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('vitrina_catalogs', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vitrina_orgs', '0001_initial'),
        ('vitrina_classifiers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('soft_deleted', models.DateTimeField(blank=True, null=True)),
                ('version', models.IntegerField(default=1)),
                ('slug', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('uuid', models.CharField(blank=True, max_length=36, null=True, unique=True)),
                ('internal_id', models.CharField(blank=True, max_length=255, null=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('title_en', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('description_en', models.TextField(blank=True, null=True)),
                ('theme', models.CharField(blank=True, max_length=255, null=True)),
                ('category_old', models.CharField(blank=True, max_length=255, null=True)),
                ('origin', models.CharField(blank=True, max_length=255, null=True)),
                ('representative_id', models.BigIntegerField(blank=True, null=True)),
                ('status', models.CharField(blank=True, choices=[('PRIORITIZED', 'Įvertinti prioritetai'), ('INVENTORED', 'Inventorintas'), ('METADATA', 'Parengti metaduomenys'), ('FINANCING', 'Įvertintas finansavimas'), ('HAS_DATA', 'Atvertas')], max_length=255, null=True)),
                ('published', models.DateTimeField(blank=True, null=True)),
                ('is_public', models.BooleanField(default=False)),
                ('language', models.CharField(blank=True, max_length=255, null=True)),
                ('spatial_coverage', models.CharField(blank=True, max_length=255, null=True)),
                ('temporal_coverage', models.CharField(blank=True, max_length=255, null=True)),
                ('update_frequency', models.CharField(blank=True, max_length=255, null=True)),
                ('last_update', models.DateTimeField(blank=True, null=True)),
                ('access_rights', models.TextField(blank=True, null=True)),
                ('distribution_conditions', models.TextField(blank=True, null=True)),
                ('tags', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('meta', models.TextField(blank=True, null=True)),
                ('priority_score', models.IntegerField(blank=True, null=True)),
                ('structure_data', models.TextField(blank=True, null=True)),
                ('structure_filename', models.CharField(blank=True, max_length=255, null=True)),
                ('financed', models.BooleanField(blank=True, null=True)),
                ('financing_plan_id', models.BigIntegerField(blank=True, null=True)),
                ('financing_priorities', models.TextField(blank=True, null=True)),
                ('financing_received', models.BigIntegerField(blank=True, null=True)),
                ('financing_required', models.BigIntegerField(blank=True, null=True)),
                ('will_be_financed', models.BooleanField(blank=True, default=False)),
                ('catalog', models.ForeignKey(blank=True, db_column='catalog', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_catalogs.catalog')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_classifiers.category')),
                ('coordinator', models.ForeignKey(blank=True, db_column='coordinator', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'dataset',
                'managed': False,
            },
            bases=(parler.models.TranslatableModel, models.Model),
        ),
        migrations.CreateModel(
            name='DatasetMigrate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('catalog_id', models.BigIntegerField(blank=True, null=True)),
                ('category', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('licence_id', models.BigIntegerField(blank=True, null=True)),
                ('organization_id', models.BigIntegerField(blank=True, null=True)),
                ('representative_id', models.BigIntegerField(blank=True, null=True)),
                ('tags', models.TextField(blank=True, null=True)),
                ('theme', models.CharField(blank=True, max_length=255, null=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('version', models.IntegerField()),
                ('update_frequency', models.CharField(blank=True, max_length=255, null=True)),
                ('internal_id', models.CharField(blank=True, max_length=255, null=True)),
                ('origin', models.CharField(blank=True, max_length=255, null=True)),
                ('published', models.DateTimeField(blank=True, null=True)),
                ('language', models.CharField(blank=True, max_length=255, null=True)),
                ('temporal_coverage', models.CharField(blank=True, max_length=255, null=True)),
                ('spatial_coverage', models.CharField(blank=True, max_length=255, null=True)),
                ('is_public', models.BooleanField(blank=True, null=True)),
                ('meta', models.TextField(blank=True, null=True)),
                ('coordinator_id', models.BigIntegerField(blank=True, null=True)),
                ('financed', models.BooleanField(blank=True, null=True)),
                ('financing_plan_id', models.BigIntegerField(blank=True, null=True)),
                ('financing_priorities', models.TextField(blank=True, null=True)),
                ('financing_received', models.BigIntegerField(blank=True, null=True)),
                ('financing_required', models.BigIntegerField(blank=True, null=True)),
                ('priority_score', models.IntegerField(blank=True, null=True)),
                ('slug', models.CharField(blank=True, max_length=255, null=True)),
                ('soft_deleted', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(blank=True, max_length=255, null=True)),
                ('uuid', models.CharField(blank=True, max_length=36, null=True, unique=True)),
                ('will_be_financed', models.BooleanField()),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'dataset_migrate',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetResource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('data', models.TextField(blank=True, null=True)),
                ('dataset_id', models.BigIntegerField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('filename', models.TextField(blank=True, null=True)),
                ('issued', models.CharField(blank=True, max_length=255, null=True)),
                ('mime', models.TextField(blank=True, null=True)),
                ('rating', models.IntegerField(blank=True, null=True)),
                ('size', models.BigIntegerField(blank=True, null=True)),
                ('spatial_coverage', models.CharField(blank=True, max_length=255, null=True)),
                ('temporal_coverage', models.CharField(blank=True, max_length=255, null=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('type', models.CharField(blank=True, max_length=255, null=True)),
                ('url', models.TextField(blank=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'dataset_resource',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetResourceMigrate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('data', models.TextField(blank=True, null=True)),
                ('dataset_id', models.BigIntegerField(blank=True, null=True)),
                ('filename', models.TextField(blank=True, null=True)),
                ('mime', models.TextField(blank=True, null=True)),
                ('rating', models.IntegerField(blank=True, null=True)),
                ('size', models.BigIntegerField(blank=True, null=True)),
                ('type', models.CharField(blank=True, max_length=255, null=True)),
                ('url', models.TextField(blank=True, null=True)),
                ('version', models.IntegerField()),
                ('description', models.TextField(blank=True, null=True)),
                ('temporal', models.CharField(blank=True, max_length=255, null=True)),
                ('title', models.CharField(blank=True, max_length=255, null=True)),
                ('spatial', models.CharField(blank=True, max_length=255, null=True)),
                ('spatial_coverage', models.CharField(blank=True, max_length=255, null=True)),
                ('temporal_coverage', models.CharField(blank=True, max_length=255, null=True)),
                ('issued', models.CharField(blank=True, max_length=255, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'dataset_resource_migrate',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='GeoportalLtEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('raw_data', models.TextField(blank=True, null=True)),
                ('type', models.TextField(blank=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'geoportal_lt_entry',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='OpenDataGovLtEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('alt_title', models.TextField(blank=True, null=True)),
                ('code', models.TextField(blank=True, null=True)),
                ('contact_info', models.TextField(blank=True, null=True)),
                ('data_extent', models.TextField(blank=True, null=True)),
                ('data_trustworthiness', models.TextField(blank=True, null=True)),
                ('dataset_begins', models.TextField(blank=True, null=True)),
                ('dataset_conditions', models.TextField(blank=True, null=True)),
                ('dataset_ends', models.TextField(blank=True, null=True)),
                ('dataset_type', models.TextField(blank=True, null=True)),
                ('date_meta_published', models.TextField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('format', models.TextField(blank=True, null=True)),
                ('keywords', models.TextField(blank=True, null=True)),
                ('publisher', models.TextField(blank=True, null=True)),
                ('refresh_period', models.TextField(blank=True, null=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('topic', models.TextField(blank=True, null=True)),
                ('url', models.TextField(blank=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'open_data_gov_lt_entry',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='HarvestingResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('published', models.BooleanField()),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('description', models.TextField(blank=True, null=True)),
                ('remote_id', models.CharField(blank=True, max_length=255, null=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('description_en', models.TextField(blank=True, null=True)),
                ('keywords', models.TextField(blank=True, null=True)),
                ('organization', models.TextField(blank=True, null=True)),
                ('raw_data', models.TextField(blank=True, null=True)),
                ('title_en', models.TextField(blank=True, null=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_classifiers.category')),
                ('job', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_catalogs.harvestingjob')),
            ],
            options={
                'db_table': 'harvesting_result',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='HarvestedVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('last_visited', models.DateTimeField(blank=True, null=True)),
                ('visit_count', models.IntegerField()),
                ('harvesting_result', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_datasets.harvestingresult')),
            ],
            options={
                'db_table': 'harvested_visit',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('last_visited', models.DateTimeField(blank=True, null=True)),
                ('visit_count', models.IntegerField()),
                ('dataset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_datasets.dataset')),
            ],
            options={
                'db_table': 'dataset_visit',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetStructureField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('data_title', models.CharField(blank=True, max_length=255, null=True)),
                ('db_table_name', models.CharField(blank=True, max_length=255, null=True)),
                ('order_id', models.IntegerField()),
                ('scheme', models.CharField(blank=True, max_length=255, null=True)),
                ('standard_title', models.CharField(blank=True, max_length=255, null=True)),
                ('technical_title', models.CharField(blank=True, max_length=255, null=True)),
                ('type', models.CharField(blank=True, max_length=255, null=True)),
                ('dataset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_datasets.dataset')),
            ],
            options={
                'db_table': 'dataset_structure_field',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetStructure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('distribution_version', models.IntegerField(blank=True, null=True)),
                ('filename', models.CharField(blank=True, max_length=255, null=True)),
                ('identifier', models.CharField(blank=True, max_length=255, null=True)),
                ('mime_type', models.CharField(blank=True, max_length=255, null=True)),
                ('size', models.BigIntegerField(blank=True, null=True)),
                ('title', models.TextField(blank=True, null=True)),
                ('standardized', models.BooleanField(blank=True, null=True)),
                ('file', models.FileField(blank=True, null=True, upload_to='files/datasets/%Y/%m/%d/')),
                ('dataset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_datasets.dataset')),
            ],
            options={
                'db_table': 'dataset_structure',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetRemark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('body', models.TextField(blank=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
                ('dataset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_datasets.dataset')),
            ],
            options={
                'db_table': 'dataset_remark',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='DatasetEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('version', models.IntegerField()),
                ('dataset_id', models.BigIntegerField(blank=True, null=True)),
                ('details', models.CharField(blank=True, max_length=255, null=True)),
                ('status', models.CharField(blank=True, max_length=255, null=True)),
                ('type', models.CharField(blank=True, max_length=255, null=True)),
                ('user', models.TextField(blank=True, null=True)),
                ('deleted', models.BooleanField(blank=True, null=True)),
                ('deleted_on', models.DateTimeField(blank=True, null=True)),
                ('user_0', models.ForeignKey(blank=True, db_column='user_id', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'dataset_event',
                'managed': False,
            },
        ),
        migrations.AddField(
            model_name='dataset',
            name='current_structure',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='vitrina_datasets.datasetstructure'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='frequency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_classifiers.frequency'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='licence',
            field=models.ForeignKey(blank=True, db_column='licence', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_classifiers.licence'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='manager_datasets', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='dataset',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='vitrina_orgs.organization'),
        ),
        migrations.AlterUniqueTogether(
            name='dataset',
            unique_together={('internal_id', 'organization_id')},
        ),
    ]
