from django.contrib.contenttypes.models import ContentType
from django.db import migrations


def fix_datasets_status(apps, schema_editor):
    Comment = apps.get_model('vitrina_comments', 'Comment')
    Dataset = apps.get_model('vitrina_datasets', 'Dataset')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    ct = ContentType.objects.get_for_model(Dataset)

    for dataset in Dataset.objects.all():
        latest_status_comment = Comment.objects.filter(content_type=ct,
                                                       object_id=dataset.pk,
                                                       status__isnull=False).order_by('-created').first()
        if latest_status_comment:
            if latest_status_comment.status == "OPENED":
                dataset.status = "HAS_DATA"
            elif latest_status_comment.status == "STRUCTURED":
                dataset.status = "HAS_STRUCTURE"
            else:
                dataset.status = "INVENTORED"
            dataset.save(update_fields=['status'])


def fix_requests_status(apps, schema_editor):
    Comment = apps.get_model('vitrina_comments', 'Comment')
    Request = apps.get_model('vitrina_requests', 'Request')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    ct = ContentType.objects.get_for_model(Request)

    for request in Request.objects.all():
        latest_status_comment = Comment.objects.filter(content_type=ct,
                                                       object_id=request.pk,
                                                       status__isnull=False).order_by('-created').first()
        if latest_status_comment:
            if request.status != latest_status_comment.status:
                request.status = latest_status_comment.status
                request.save(update_fields=['status'])


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_comments', '0005_auto_20221024_1403'),
        ('vitrina_datasets', '0012_merge_20221108_0847')
    ]

    operations = [
        migrations.RunPython(fix_datasets_status),
        migrations.RunPython(fix_requests_status),
    ]