# Generated by Django 3.2.21 on 2023-09-19 06:05

from django.db import migrations

from vitrina import settings


def assign_dataset_status(apps, schema_editor):
    Dataset = apps.get_model('vitrina_datasets', 'Dataset')
    Comment = apps.get_model('vitrina_comments', 'Comment')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    User = apps.get_model('vitrina_users', 'User')

    sys_user = User.objects.filter(email=settings.SYSTEM_USER_EMAIL).first()
    if not sys_user:
        User.objects.create(
            first_name="Sistemos",
            last_name="Naudotojas",
            email=settings.SYSTEM_USER_EMAIL,
            password="",
            is_staff=True
        )

    ct = ContentType.objects.get_for_model(Dataset)

    for dataset in Dataset.objects.filter(
        is_public=True,
        published__isnull=False,
        status__isnull=True,
    ):
        if (
            not dataset.datasetdistribution_set.exists() and
            not dataset.plandataset_set.exists() and
            not dataset.datasetstructure_set.exists()
        ):
            dataset.status = "INVENTORED"
            dataset.save(update_fields=['status'])

            Comment.objects.create(
                created=dataset.created,
                content_type=ct,
                object_id=dataset.pk,
                user=sys_user,
                type="STATUS",
                status="INVENTORED"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_datasets', '0020_auto_20230911_0840'),
        ('vitrina_comments', '0007_auto_20230522_1627'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('vitrina_users', '0007_auto_20230905_1610'),
    ]

    operations = [
        migrations.RunPython(assign_dataset_status),
    ]