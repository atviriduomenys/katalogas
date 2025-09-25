from django.db import migrations

def create_groups_with_permissions(groups_permissions, app_label, apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    for group_name, permission_codenames in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if not created:
            continue
        for codename in permission_codenames:
            permission = Permission.objects.get(
                codename=codename,
                content_type__app_label=app_label
            )
            group.permissions.add(permission)

def create_organization_groups(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')

    org_permissions = Permission.objects.filter(
        content_type__app_label='vitrina_orgs',
        content_type__model='organization'
    ).values_list('codename', flat=True)

    org_groups = {
        'Organization Viewers': ['view_organization'],
        'Organization Managers': list(org_permissions),
    }
    create_groups_with_permissions(org_groups, 'vitrina_orgs', apps, schema_editor)

class Migration(migrations.Migration):
    dependencies = [
        ('vitrina_orgs', '0005_delete_agent'),
    ]

    operations = [
        migrations.RunPython(create_organization_groups, migrations.RunPython.noop),
    ]