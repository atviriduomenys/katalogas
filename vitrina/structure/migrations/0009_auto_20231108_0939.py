# Generated by Django 3.2.22 on 2023-11-08 07:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_structure', '0008_auto_20231106_1015'),
    ]

    operations = [
        migrations.AddField(
            model_name='metadataversion',
            name='access',
            field=models.IntegerField(blank=True, choices=[(None, 'nepasirinkta'), (0, 'private'), (1, 'protected'), (2, 'public'), (3, 'open')], null=True, verbose_name='Prieiga'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='base',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='vitrina_structure.base', verbose_name='Bazė'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='level_given',
            field=models.IntegerField(blank=True, null=True, verbose_name='Duotas brandos lygis'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Vardas'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='prepare',
            field=models.CharField(blank=True, max_length=255, verbose_name='Formulė'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='ref',
            field=models.CharField(blank=True, max_length=255, verbose_name='Ryšys'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='required',
            field=models.BooleanField(blank=True, null=True, verbose_name='Privalomas'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='source',
            field=models.CharField(blank=True, max_length=255, verbose_name='Šaltinis'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='type',
            field=models.CharField(blank=True, max_length=255, verbose_name='Tipas'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='type_args',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Tipo argumentai'),
        ),
        migrations.AddField(
            model_name='metadataversion',
            name='unique',
            field=models.BooleanField(blank=True, null=True, verbose_name='Unikalus'),
        ),
    ]