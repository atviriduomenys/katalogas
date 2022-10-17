# Generated by Django 3.2.16 on 2022-10-10 11:18

import collections

from django.db import migrations


def create_history_objects(apps, schema_editor):
    RequestEvent = apps.get_model('vitrina_requests', 'RequestEvent')
    Request = apps.get_model('vitrina_requests', 'Request')
    Revision = apps.get_model('reversion', 'Revision')
    Version = apps.get_model('reversion', 'Version')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    User = apps.get_model('vitrina_users', 'User')

    users = collections.defaultdict(dict)
    for user in User.objects.filter(organization_id__isnull=False):
        org = user.organization_id
        user_name = f'{user.first_name} {user.last_name}'
        users[org][user_name] = user

    for event in RequestEvent.objects.all():
        if event.request_id:
            content_type = ContentType.objects.get_for_model(Request)
            request = Request.objects.get(pk=event.request_id)
            revision = Revision.objects.create(
                date_created=event.created,
                comment=event.type or "",
                user=users.get(request.organization_id, {}).get(event.meta)
            )
            Version.objects.create(
                object_id=event.request_id,
                content_type=content_type,
                object_repr=str(request),
                format="json",
                db="default",
                revision=revision
            )


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_requests', '0001_initial'),
        ('vitrina_orgs', '0007_auto_20220928_1451'),
        ('vitrina_users', '0004_auto_20220909_1301'),
    ]

    operations = [
        migrations.RunPython(create_history_objects)
    ]
