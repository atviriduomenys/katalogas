# Generated by Django 3.2.19 on 2023-06-29 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_tasks', '0004_auto_20221213_1237'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='role',
            field=models.CharField(blank=True, choices=[('manager', 'Organizacijos tvarkytojas'), ('coordinator', 'Organizacijos koordinatorius'), ('supervisor', 'Vyr. koordinatorius')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]