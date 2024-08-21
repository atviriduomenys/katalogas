# Generated by Django 3.2.25 on 2024-08-21 06:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vitrina_orgs', '0024_auto_20240205_1319'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='publishedreport',
            options={'managed': True, 'verbose_name': 'Ataskaita', 'verbose_name_plural': 'Ataskaitos'},
        ),
        migrations.AddField(
            model_name='representativerequest',
            name='created',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Sukurta'),
        ),
        migrations.AddField(
            model_name='representativerequest',
            name='email',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='El. paštas'),
        ),
        migrations.AddField(
            model_name='representativerequest',
            name='phone',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Telefono numeris'),
        ),
        migrations.AddField(
            model_name='representativerequest',
            name='status',
            field=models.CharField(blank=True, choices=[('CREATED', 'Pateiktas'), ('APPROVED', 'Patvirtintas'), ('REJECTED', 'Atmestas')], max_length=255, null=True, verbose_name='Būsena'),
        ),
        migrations.AlterField(
            model_name='organization',
            name='kind',
            field=models.CharField(choices=[('org', 'Nepelno ir nevalstybinė organizacija'), ('com', 'Verslo organizacija'), ('gov', 'Valstybinė įstaiga')], default='org', max_length=36, verbose_name='Tipas'),
        ),
        migrations.AlterField(
            model_name='publishedreport',
            name='data',
            field=models.TextField(blank=True, null=True, verbose_name='Duomenys'),
        ),
        migrations.AlterField(
            model_name='publishedreport',
            name='title',
            field=models.TextField(blank=True, null=True, verbose_name='Pavadinimas'),
        ),
        migrations.AlterField(
            model_name='representativerequest',
            name='document',
            field=models.FileField(upload_to='data/files/request_assignments', verbose_name='Pridėtas dokumentas'),
        ),
        migrations.AlterField(
            model_name='representativerequest',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vitrina_orgs.organization', verbose_name='Organizacija'),
        ),
        migrations.AlterField(
            model_name='representativerequest',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Naudotojas'),
        ),
    ]
