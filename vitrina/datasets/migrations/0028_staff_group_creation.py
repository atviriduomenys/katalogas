from django.db import migrations
from django.contrib.auth.models import Group, Permission


def create_groups_with_permissions(groups_permissions, app_label):
    for group_name, permission_codenames in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)

        if not created:
            return

        for codename in permission_codenames:
            permission = Permission.objects.get(
                codename=codename,
                content_type__app_label=app_label
            )
            group.permissions.add(permission)


def create_dataset_report_groups(apps, schema_editor):
    report_groups = {
        'Dataset Report Users': [
            'view_datasetreport',
        ],
    }
    create_groups_with_permissions(report_groups, 'vitrina_datasets')


def create_dataset_groups(apps, schema_editor):
    dataset_groups = {
        'Dataset Viewers': ['view_dataset'],
        'Dataset Editors': ['view_dataset', 'add_dataset', 'change_dataset'],
        'Dataset Managers': ['view_dataset', 'add_dataset', 'change_dataset', 'delete_dataset'],
    }
    create_groups_with_permissions(dataset_groups, 'vitrina_datasets')


def create_dataset_tag_groups(apps, schema_editor):
    tag_groups = {
        'Dataset Tag Viewers': ['view_tagulous_dataset_tags'],
        'Dataset Tag Editors': ['view_tagulous_dataset_tags', 'add_tagulous_dataset_tags', 'change_tagulous_dataset_tags'],
        'Dataset Tag Managers': ['view_tagulous_dataset_tags', 'add_tagulous_dataset_tags', 'change_tagulous_dataset_tags', 'delete_tagulous_dataset_tags'],
    }
    create_groups_with_permissions(tag_groups, 'vitrina_datasets')


class Migration(migrations.Migration):
    dependencies = [
        ('vitrina_datasets', '0027_merge_20250916_0655'),
    ]

    operations = [
        migrations.RunPython(create_dataset_groups, migrations.RunPython.noop),
        migrations.RunPython(create_dataset_tag_groups, migrations.RunPython.noop),
        migrations.RunPython(create_dataset_report_groups, migrations.RunPython.noop),
    ]
