# Generated by Django 3.2.16 on 2022-12-13 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_tasks', '0003_auto_20221129_0819'),
    ]

    operations = [
        migrations.CreateModel(
            name='Holiday',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('title', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'holiday',
            },
        ),
    ]
