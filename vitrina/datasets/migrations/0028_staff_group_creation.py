from django.db import migrations
from django.contrib.auth.models import Group, Permission

def create_dataset_groups(apps, schema_editor):
    groups_permissions = {
        'Dataset Viewers': [
            'view_dataset',
        ],
        'Dataset Editors': [
            'view_dataset', 'add_dataset', 'change_dataset',
        ],
        'Dataset Managers': [
            'view_dataset', 'add_dataset', 'change_dataset', 'delete_dataset',
        ],
    }

    for group_name, permission_codenames in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)

        if not created:
            return

        for codename in permission_codenames:
            permission = Permission.objects.get(
                codename=codename,
                content_type__app_label='vitrina_datasets'
            )
            group.permissions.add(permission)

class Migration(migrations.Migration):
    dependencies = [
        ('vitrina_datasets', '0027_merge_20250916_0655'),
    ]

    operations = [
        migrations.RunPython(create_dataset_groups),
    ]