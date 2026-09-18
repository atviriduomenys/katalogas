from importlib import import_module

from django.db import migrations

from vitrina.cms.stories_migrations._helpers import remap_generic_relations


upstream = import_module("djangocms_stories.migrations.0002_auto_20250618_1556")


def remap_file_resources(apps, pk_maps, source_model, target_model):
    """Move the news attachments onto the ids the posts were copied to.

    pk_maps.get, not pk_maps["Post"]: upstream fills that key inside its
    per-row loop, so a database that has the blog tables but no posts in them
    never gets one, and asking for it directly would end the deployment with a
    KeyError.
    """
    ContentType = apps.get_model("contenttypes", "ContentType")
    FileResource = apps.get_model("vitrina_cms", "FileResource")
    remap_generic_relations(
        FileResource,
        source_content_type=ContentType.objects.get_for_model(source_model),
        target_content_type=ContentType.objects.get_for_model(target_model),
        object_id_map=pk_maps.get("Post", {}),
    )


def migrate_from_blog_to_stories(apps, schema_editor):
    original_copy_data = upstream.copy_data

    def copy_data(pk_maps, pass_2, source_model, target_model):
        original_copy_data(pk_maps, pass_2, source_model, target_model)
        if target_model._meta.label_lower != "djangocms_stories.post":
            return

        remap_file_resources(apps, pk_maps, source_model, target_model)

    upstream.copy_data = copy_data
    try:
        upstream.migrate_from_blog_to_stories(apps, schema_editor)
    finally:
        upstream.copy_data = original_copy_data


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_stories", "0001_initial"),
        ("vitrina_cms", "0006_deployment_is_published_deployment_level"),
    ]

    operations = [
        migrations.RunPython(
            code=migrate_from_blog_to_stories,
            elidable=True,
        ),
        migrations.RunPython(
            code=upstream.adjust_apphooks,
            elidable=True,
        ),
    ]
