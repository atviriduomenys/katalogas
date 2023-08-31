# Generated by Django 3.2.20 on 2023-08-17 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_tasks', '0013_auto_20230810_1343'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='role',
            field=models.CharField(blank=True, choices=[('manager', 'Organizacijos tvarkytojas'), ('coordinator', 'Organizacijos koordinatorius'), ('supervisor', 'Vyr. koordinatorius')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='type',
            field=models.CharField(choices=[('comment', 'Komentaras'), ('request', 'Prašymas'), ('error', 'Klaida'), ('error_frequency', 'Klaida atnaujinimo dažnume'), ('error_distribution', 'Klaida duomenų rinkinio šaltinyje')], default='comment', max_length=255),
        ),
    ]
