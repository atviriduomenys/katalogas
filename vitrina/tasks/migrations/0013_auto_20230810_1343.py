# Generated by Django 3.2.20 on 2023-08-10 10:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_tasks', '0012_auto_20230810_1058'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='assigned',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='completed',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='role',
            field=models.CharField(blank=True, choices=[('supervisor', 'Vyr. koordinatorius'), ('manager', 'Organizacijos tvarkytojas'), ('coordinator', 'Organizacijos koordinatorius')], max_length=255, null=True),
        ),
    ]
