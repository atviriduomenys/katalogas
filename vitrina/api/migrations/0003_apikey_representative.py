# Generated by Django 3.2.16 on 2022-11-03 07:16

from django.db import migrations, models
import django.db.models.deletion


def create_representative_api_keys(apps, schema_editor):
    ApiKey = apps.get_model('vitrina_api', 'ApiKey')
    Representative = apps.get_model('vitrina_orgs', 'Representative')
    Organization = apps.get_model('vitrina_orgs', 'Organization')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    ct = ContentType.objects.get_for_model(Organization)

    for key in ApiKey.objects.all():
        if key.organization:
            for rep in Representative.objects.filter(content_type=ct, object_id=key.organization.pk):
                ApiKey.objects.create(
                    version=key.version,
                    api_key=key.api_key,
                    enabled=key.enabled,
                    expires=key.expires,
                    representative=rep
                )
                rep.has_api_access = True
                rep.save()


def delete_non_representative_api_keys(apps, schema_editor):
    ApiKey = apps.get_model('vitrina_api', 'ApiKey')

    ApiKey.objects.filter(representative__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_api', '0002_alter_apikey_options'),
        ('vitrina_orgs', '0014_auto_20221103_1225'),
    ]

    operations = [
        migrations.RunSQL("do $$ declare i record; " +
                          "begin for i in select idx.relname as name " +
                          "from pg_index pgi " +
                          "join pg_class idx on idx.oid = pgi.indexrelid " +
                          "join pg_class tbl on tbl.oid = pgi.indrelid " +
                          "where pgi.indisunique and not pgi.indisprimary and tbl.relname = 'api_key' " +
                          "loop " +
                          "execute 'ALTER TABLE api_key DROP CONSTRAINT IF EXISTS ' || i.name; " +
                          "execute 'DROP INDEX IF EXISTS ' || i.name; " +
                          "end loop; " +
                          "end; $$;"),

        migrations.AddField(
            model_name='apikey',
            name='representative',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vitrina_orgs.representative'),
        ),
        migrations.AlterField(
            model_name='apikey',
            name='api_key',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.RunPython(create_representative_api_keys),
        migrations.RunPython(delete_non_representative_api_keys),
        migrations.RemoveField(
            model_name='apikey',
            name='organization',
        )
    ]