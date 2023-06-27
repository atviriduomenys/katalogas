# Generated by Django 3.2.16 on 2023-05-22 13:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('vitrina_comments', '0006_fix_statuses_for_dataset_and_request'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comment',
            options={'get_latest_by': 'created', 'ordering': ('-created',)},
        ),
        migrations.AlterModelOptions(
            name='suggestion',
            options={'managed': True},
        ),
        migrations.AddField(
            model_name='comment',
            name='external_content_type',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='comment',
            name='external_object_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='comment',
            name='content_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='content_type_comments', to='contenttypes.contenttype'),
        ),
        migrations.AlterField(
            model_name='comment',
            name='created',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='comment',
            name='object_id',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='comment',
            name='type',
            field=models.CharField(choices=[('USER', 'Naudotojo komentaras'), ('REQUEST', 'Prašymo atverti duomenis komentaras'), ('PROJECT', 'Duomenų rinkinio įtraukimo į projektą komentaras'), ('STATUS', 'Statuso keitimo komentaras'), ('STRUCTURE', 'Struktūros importavimo komentaras'), ('STRUCTURE_ERROR', 'Struktūros importavimo klaida')], default='USER', max_length=255),
        ),
    ]
