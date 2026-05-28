from django.db import migrations

def create_groups_with_permissions(groups_permissions, app_label, apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    for group_name, permission_codenames in groups_permissions.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if not created:
            continue
        for codename in permission_codenames:
            try:
                permission = Permission.objects.get(
                    codename=codename,
                    content_type__app_label=app_label
                )
                group.permissions.add(permission)
            except Permission.DoesNotExist:
                # Skip for tests
                continue


def create_blog_groups(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')

    blog_permissions = Permission.objects.filter(
        content_type__app_label='djangocms_stories'
    ).values_list('codename', flat=True)

    blog_groups = {
        'Blog Administrators': list(blog_permissions),
    }
    create_groups_with_permissions(blog_groups, 'djangocms_stories', apps, schema_editor)


def create_cms_groups(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    core_page_models = ['page', 'title']
    cms_permissions = []

    for model_name in core_page_models:
        try:
            content_type = ContentType.objects.get(
                app_label='cms',
                model=model_name
            )
            model_permissions = Permission.objects.filter(
                content_type=content_type
            ).values_list('codename', flat=True)
            cms_permissions.extend(list(model_permissions))
        except ContentType.DoesNotExist:
            continue

    essential_permissions = ['publish_page', 'use_structure']
    for perm in essential_permissions:
        if perm not in cms_permissions:
            cms_permissions.append(perm)

    cms_groups = {
        'CMS Administrators': cms_permissions,
    }
    create_groups_with_permissions(cms_groups, 'cms', apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        ('vitrina_users', '0002_initial'),
        ('cms', '0022_auto_20180620_1551'),
        ('filer', '0012_file_mime_type'),
    ]

    operations = [
        migrations.RunPython(create_blog_groups, migrations.RunPython.noop),
        migrations.RunPython(create_cms_groups, migrations.RunPython.noop),
    ]