# Generated by Django 3.2.16 on 2022-12-21 07:01

from django.db import migrations, models


def disable_non_unique_keys(apps, schema_editor):
    ApiKey = apps.get_model('vitrina_api', 'ApiKey')

    non_unique_keys = list(
        ApiKey.objects.values_list('api_key', flat=True)
        .annotate(count=models.Count('api_key'))
        .filter(count__gt=1)
    )
    for idx, key in enumerate(ApiKey.objects.filter(api_key__in=non_unique_keys)):
        key.api_key = f"DUPLICATE-{idx}-{key.api_key}"
        key.enabled = False
        key.save(update_fields=['api_key', 'enabled'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_api', '0003_apikey_representative'),
    ]

    operations = [
        migrations.RunPython(disable_non_unique_keys),
        migrations.AlterField(
            model_name='apikey',
            name='api_key',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
