# Generated by Django 3.2.15 on 2022-09-19 07:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_classifiers', '0007_remake_categories'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='path',
            field=models.CharField(unique=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='category',
            name='numchild',
            field=models.PositiveIntegerField(),
        ),
    ]

