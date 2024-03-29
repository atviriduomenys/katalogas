# Generated by Django 3.2.16 on 2022-10-24 08:13

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_users(apps, schema_editor):
    Comment = apps.get_model('vitrina_comments', 'Comment')
    for comment in Comment.objects.all():
        if comment.author_id:
            comment.user_id = comment.author_id
            comment.save(update_fields=['user_id'])


def migrate_datasets(apps, schema_editor):
    Comment = apps.get_model('vitrina_comments', 'Comment')
    Dataset = apps.get_model('vitrina_datasets', 'Dataset')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for comment in Comment.objects.all():
        if comment.dataset_id:
            comment.content_type = ContentType.objects.get_for_model(Dataset)
            comment.object_id = comment.dataset_id
            comment.save(update_fields=['content_type', 'object_id'])


def migrate_requests(apps, schema_editor):
    Comment = apps.get_model('vitrina_comments', 'Comment')
    Request = apps.get_model('vitrina_requests', 'Request')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for comment in Comment.objects.all():
        if comment.request_id:
            comment.content_type = ContentType.objects.get_for_model(Request)
            comment.object_id = comment.request_id
            comment.save(update_fields=['content_type', 'object_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vitrina_comments', '0002_auto_20221024_1106'),
        ('vitrina_datasets', '0001_initial'),
        ('vitrina_requests', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='content_type_comments',
                                    to='contenttypes.contenttype', default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='comment',
            name='rel_content_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='rel_content_type_comments', to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='comment',
            name='is_public',
            field=models.BooleanField(default=True, verbose_name='Viešas komentaras'),
        ),
        migrations.AddField(
            model_name='comment',
            name='object_id',
            field=models.PositiveIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='comment',
            name='rel_object_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='comment',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='vitrina_users.user'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='comment',
            name='created',
            field=models.DateTimeField(blank=True, default=datetime.datetime.now, null=True),
        ),
        migrations.RunPython(migrate_users),
        migrations.RunPython(migrate_datasets),
        migrations.RunPython(migrate_requests),
    ]
