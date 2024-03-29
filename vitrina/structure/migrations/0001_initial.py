# Generated by Django 3.2.16 on 2023-05-05 12:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('vitrina_datasets', '0014_merge_0013_auto_20221202_0923_0013_auto_20221206_1003'),
        ('vitrina_resources', '0014_fix_dates'),
    ]

    operations = [
        migrations.CreateModel(
            name='Base',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name': 'Bazė',
                'db_table': 'base',
            },
        ),
        migrations.CreateModel(
            name='Enum',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Pavadinimas')),
                ('object_id', models.PositiveIntegerField(verbose_name='Objekto id')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='Objekto tipas')),
            ],
            options={
                'verbose_name': 'Pasirinkimų sąrašas',
                'db_table': 'enum',
            },
        ),
        migrations.CreateModel(
            name='Model',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('base', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='base_models', to='vitrina_structure.base', verbose_name='Bazė')),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vitrina_datasets.dataset', verbose_name='Duomenų rinkinys')),
                ('distribution', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='vitrina_resources.datasetdistribution', verbose_name='Duomenų šaltinis')),
            ],
            options={
                'verbose_name': 'Modelis',
                'db_table': 'model',
            },
        ),
        migrations.CreateModel(
            name='Param',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Pavadinimas')),
                ('object_id', models.PositiveIntegerField(verbose_name='Objekto id')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='Objekto tipas')),
            ],
            options={
                'verbose_name': 'Parametras',
                'db_table': 'param',
            },
        ),
        migrations.CreateModel(
            name='Property',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('given', models.BooleanField(default=True, verbose_name='Duota savybė')),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='model_properties', to='vitrina_structure.model', verbose_name='Modelis')),
                ('property', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_properties', to='vitrina_structure.property', verbose_name='Tėvinė savybė')),
                ('ref_model', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ref_model_properties', to='vitrina_structure.model', verbose_name='Susijęs modelis')),
            ],
            options={
                'verbose_name': 'Savybė',
                'db_table': 'property',
            },
        ),
        migrations.CreateModel(
            name='PropertyList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField(verbose_name='Rikiavimo tvarka')),
                ('object_id', models.PositiveIntegerField(verbose_name='Objekto id')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='Objekto tipas')),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vitrina_structure.property', verbose_name='Savybė')),
            ],
            options={
                'verbose_name': 'Savybių sąrašas',
                'db_table': 'property_list',
            },
        ),
        migrations.CreateModel(
            name='Prefix',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Pavadinimas')),
                ('uri', models.CharField(max_length=255, verbose_name='URI')),
                ('object_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='Objekto id')),
                ('content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contenttypes.contenttype', verbose_name='Objekto tipas')),
            ],
            options={
                'verbose_name': 'Prefiksas',
                'db_table': 'prefix',
            },
        ),
        migrations.CreateModel(
            name='ParamItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('param', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vitrina_structure.param', verbose_name='Parametras')),
            ],
            options={
                'verbose_name': 'Parametro dalis',
                'db_table': 'param_item',
            },
        ),
        migrations.CreateModel(
            name='Metadata',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.CharField(max_length=255, verbose_name='Id')),
                ('name', models.CharField(blank=True, max_length=255, verbose_name='Vardas')),
                ('type', models.CharField(blank=True, max_length=255, verbose_name='Tipas')),
                ('ref', models.CharField(blank=True, max_length=255, verbose_name='Ryšys')),
                ('source', models.CharField(blank=True, max_length=255, verbose_name='Šaltinis')),
                ('prepare', models.CharField(blank=True, max_length=255, verbose_name='Formulė')),
                ('prepare_ast', models.JSONField(blank=True, verbose_name='Formulės AST')),
                ('level', models.IntegerField(blank=True, null=True, verbose_name='Brandos lygis')),
                ('level_given', models.IntegerField(blank=True, null=True, verbose_name='Duotas brandos lygis')),
                ('access', models.CharField(blank=True, max_length=255, verbose_name='Prieiga')),
                ('uri', models.CharField(blank=True, max_length=255, verbose_name='Žodyno atitikmuo')),
                ('version', models.IntegerField(blank=True, verbose_name='Versija')),
                ('title', models.CharField(blank=True, max_length=255, verbose_name='Pavadinimas')),
                ('description', models.CharField(blank=True, max_length=255, verbose_name='Aprašymas')),
                ('order', models.IntegerField(blank=True, null=True, verbose_name='Rikiavimo tvarka')),
                ('object_id', models.PositiveIntegerField(verbose_name='Objekto id')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='Objekto tipas')),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vitrina_datasets.dataset', verbose_name='Duomenų rinkinys')),
                ('prefix', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='vitrina_structure.prefix', verbose_name='Prefiksas')),
            ],
            options={
                'verbose_name': 'Metaduomenys',
                'db_table': 'metadata',
            },
        ),
        migrations.CreateModel(
            name='EnumItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enum', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vitrina_structure.enum', verbose_name='Pasirinkimų sąrašas')),
            ],
            options={
                'verbose_name': 'Pasirinkimas',
                'db_table': 'enum_item',
            },
        ),
        migrations.AddField(
            model_name='base',
            name='model',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ref_model_base', to='vitrina_structure.model', verbose_name='Paveldimas modelis'),
        ),
    ]
