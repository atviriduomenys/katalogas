# Generated by Django 3.2.23 on 2023-12-11 09:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0018_auto_20231108_1027'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='distributionformat',
            options={'managed': True},
        ),
        migrations.AddField(
            model_name='datasetdistribution',
            name='upload_to_storage',
            field=models.BooleanField(default=False, verbose_name='Įkėlimas į saugyklą'),
        ),
        migrations.AlterField(
            model_name='datasetdistribution',
            name='download_url',
            field=models.TextField(blank=True, help_text='Tiesioginė duomenų atsisiuntimo nuoroda.',
                                   null=True, verbose_name='Atsisiuntimo nuoroda'),
        ),
        migrations.AlterField(
            model_name='datasetdistribution',
            name='format',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='vitrina_resources.format', verbose_name='Duomenų formatas'),
        ),
        migrations.AlterField(
            model_name='format',
            name='version',
            field=models.IntegerField(default=1),
        ),
    ]
