# Generated by Django 3.2.16 on 2022-10-19 12:10

from django.db import migrations


def create_history_objects(apps, schema_editor):
    Project = apps.get_model('vitrina_projects', 'Project')
    Revision = apps.get_model('reversion', 'Revision')
    Version = apps.get_model('reversion', 'Version')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    for project in Project.objects.all():
        content_type = ContentType.objects.get_for_model(Project)
        revision = Revision.objects.create(
            date_created=project.created,
            comment="CREATED",
            user=project.user,
        )
        Version.objects.create(
            object_id=project.id,
            content_type=content_type,
            object_repr=str(project),
            format="json",
            db="default",
            revision=revision,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_projects', '0003_auto_20220901_1239'),
    ]

    operations = [
        migrations.RunPython(create_history_objects)
    ]