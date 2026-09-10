from importlib import import_module


import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from djangocms_stories.cms_appconfig import StoriesConfig, config_defaults
from djangocms_stories.models import Post, PostContent

from djangocms_versioning.models import Version

from vitrina.cms.models import FileResource
from vitrina.cms.stories_migrations._helpers import remap_generic_relations
from vitrina.cms.views import PostDetailView
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_attachments_are_found_through_the_post_not_its_content():
    """Attachments hang off the post; the view's object is the post's content.

    scripts/migrate_news.py stored every news attachment against the post
    itself. A lookup keyed on the content object asks for a different content
    type, finds nothing, and the files vanish from the page without any error.
    """
    config = StoriesConfig.objects.create(namespace="stories", **config_defaults)
    post = Post.objects.create(app_config=config)
    content = PostContent.admin_manager.create(post=post, title="Naujiena", slug="naujiena", language="lt")
    Version.objects.create(content=content, created_by=UserFactory(), state="published")
    attachment = FileResource.objects.create(
        version=1,
        content_type=ContentType.objects.get_for_model(post),
        object_id=post.pk,
    )

    view = PostDetailView()
    view.request = RequestFactory().get("/")
    view.kwargs = {"slug": content.slug}
    view.config = config
    view.object = content
    context = view.get_context_data(object=content)

    assert list(context["files"]) == [attachment]

    # And the lookup the view used to do returns nothing, which is why this
    # went unnoticed: no error, just an article with its attachments gone.
    assert not FileResource.objects.filter(
        content_type=ContentType.objects.get_for_model(content),
        object_id=content.pk,
    ).exists()


@pytest.mark.django_db
def test_legacy_attachments_are_remapped_to_the_new_post_ids():
    legacy_content_type, _ = ContentType.objects.get_or_create(
        app_label="djangocms_blog",
        model="post",
    )
    stories_content_type = ContentType.objects.get_for_model(Post)
    post = Post.objects.create()
    attachment = FileResource.objects.create(
        version=1,
        content_type=legacy_content_type,
        object_id=41,
    )

    remap_generic_relations(
        FileResource,
        source_content_type=legacy_content_type,
        target_content_type=stories_content_type,
        object_id_map={41: post.pk},
    )

    attachment.refresh_from_db()
    assert attachment.content_type == stories_content_type
    assert attachment.object_id == post.pk


@pytest.mark.django_db
def test_the_remap_survives_a_blog_with_no_posts():
    """Upstream only records the id map while copying rows.

    A database that still has the blog tables but nothing in them copies
    nothing, so the "Post" key is never created - and reaching for it directly
    would end the deployment with a KeyError before anything else ran.
    """
    from importlib import import_module

    from django.apps import apps as global_apps

    migration = import_module("vitrina.cms.stories_migrations.0002_auto_20250618_1556")

    migration.remap_file_resources(global_apps, {}, Post, Post)


def _fake_model(label):
    from types import SimpleNamespace

    return SimpleNamespace(_meta=SimpleNamespace(label_lower=label))


def _run_wrapper_with(monkeypatch, fake_migration):
    """Drive the mirrored migration's wrapper with a stand-in upstream."""
    module = import_module("vitrina.cms.stories_migrations.0002_auto_20250618_1556")
    copied, remapped = [], []

    monkeypatch.setattr(module.upstream, "copy_data", lambda *args: copied.append(args))
    monkeypatch.setattr(module.upstream, "migrate_from_blog_to_stories", fake_migration)
    monkeypatch.setattr(module, "remap_file_resources", lambda *args: remapped.append(args))

    return module, copied, remapped


def test_the_wrapper_remaps_attachments_only_for_the_post_model(monkeypatch):
    """Upstream calls copy_data per model; only the Post pass carries our ids.

    Nothing else runs this wrapper - the tests around it call
    remap_generic_relations directly - so a change in the callback's arguments
    would first be noticed while migrating production.
    """
    module = import_module("vitrina.cms.stories_migrations.0002_auto_20250618_1556")
    pk_maps = {"Post": {1: 11}}
    post = _fake_model("djangocms_stories.post")
    category = _fake_model("djangocms_stories.postcategory")

    def fake_migration(apps, schema_editor):
        module.upstream.copy_data(pk_maps, False, _fake_model("djangocms_blog.blogcategory"), category)
        module.upstream.copy_data(pk_maps, False, _fake_model("djangocms_blog.post"), post)

    module, copied, remapped = _run_wrapper_with(monkeypatch, fake_migration)
    module.migrate_from_blog_to_stories(apps="apps", schema_editor=None)

    # Upstream still sees both passes, unchanged.
    assert len(copied) == 2
    # Ours runs once, for the post, and is handed the map upstream filled.
    assert len(remapped) == 1
    assert remapped[0][1] is pk_maps
    assert remapped[0][3] is post


def test_the_wrapper_puts_upstreams_copy_data_back(monkeypatch):
    """Including when the migration blows up: the patch outlives the failure."""
    module = import_module("vitrina.cms.stories_migrations.0002_auto_20250618_1556")

    def fake_migration(apps, schema_editor):
        raise RuntimeError("First run 'python manage migrate djangocms_blog'.")

    module, _, _ = _run_wrapper_with(monkeypatch, fake_migration)
    patched = module.upstream.copy_data

    with pytest.raises(RuntimeError):
        module.migrate_from_blog_to_stories(apps="apps", schema_editor=None)

    assert module.upstream.copy_data is patched
