# Generated by Django 3.2.14 on 2022-09-13 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_orgs', '0002_alter_organization_kind'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organization',
            name='kind',
            field=models.CharField(choices=[('gov', 'Valstybinė įstaiga'), ('org', 'Nepelno ir nevalstybinė organizacija'), ('com', 'Verslo organizacija')], default='org', max_length=36),
        ),
    ]
