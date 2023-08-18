# Generated by Django 3.2.20 on 2023-08-17 19:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_comments', '0007_auto_20230522_1627'),
        ('vitrina_tasks', '0015_auto_20230817_1412'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='comment_object',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='vitrina_comments.comment'),
        ),
        migrations.AlterField(
            model_name='task',
            name='role',
            field=models.CharField(blank=True, choices=[('coordinator', 'Organizacijos koordinatorius'), ('manager', 'Organizacijos tvarkytojas'), ('supervisor', 'Vyr. koordinatorius')], max_length=255, null=True),
        ),
    ]
