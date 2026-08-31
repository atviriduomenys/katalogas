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
def test_moving_post_text_refuses_when_placeholders_are_off():
    """The command clears post_text, and post_text is what the page shows.

    post_detail.html renders the placeholder only when the app config asks for
    it and falls back to post_text otherwise, so running this against a config
    with placeholders off empties every article it touches.
    """
    from django.core.management import call_command
    from django.core.management.base import CommandError

    config = StoriesConfig.objects.create(namespace="off", **{**config_defaults, "use_placeholder": False})
    post = Post.objects.create(app_config=config)
    PostContent.admin_manager.create(
        post=post, title="Naujiena", slug="naujiena", language="lt", post_text="<p>Tekstas</p>"
    )

    with pytest.raises(CommandError, match="off"):
        call_command("migrate_post_text_to_placeholder")

    assert PostContent.admin_manager.get(post=post).post_text == "<p>Tekstas</p>"


@pytest.mark.django_db
def test_moving_post_text_refuses_when_a_post_has_no_config():
    """A post with no app config falls back to post_text as well.

    The template asks the config whether to use placeholders, and there is no
    config to ask - so the article is rendered from post_text, which this
    command clears.
    """
    from django.core.management import call_command
    from django.core.management.base import CommandError

    post = Post.objects.create()
    PostContent.admin_manager.create(
        post=post, title="Naujiena", slug="naujiena", language="lt", post_text="<p>Tekstas</p>"
    )

    with pytest.raises(CommandError):
        call_command("migrate_post_text_to_placeholder")

    assert PostContent.admin_manager.get(post=post).post_text == "<p>Tekstas</p>"


@pytest.mark.django_db
def test_moving_post_text_into_the_placeholder():
    """The command's own job: the html becomes a plugin and the field is cleared."""
    from cms.api import add_plugin
    from cms.models import CMSPlugin
    from django.core.management import call_command
    from djangocms_stories.cms_appconfig import StoriesConfig, config_defaults

    config = StoriesConfig.objects.create(namespace="on", **{**config_defaults, "use_placeholder": True})
    post = Post.objects.create(app_config=config)
    content = PostContent.admin_manager.create(
        post=post, title="Naujiena", slug="naujiena", language="lt", post_text="<p>Senas tekstas</p>"
    )
    CMSPlugin.objects.filter(placeholder=content.content).delete()
    add_plugin(content.content, "TextPlugin", "lt", body="<p>Jau esamas</p>")

    call_command("migrate_post_text_to_placeholder")

    content.refresh_from_db()
    assert content.post_text == ""
    bodies = [
        p.get_plugin_instance()[0].body
        for p in CMSPlugin.objects.filter(placeholder=content.content).order_by("position")
    ]
    # The article body goes in front of whatever was already there.
    assert bodies == ["<p>Senas tekstas</p>", "<p>Jau esamas</p>"]


@pytest.mark.django_db
def test_dry_run_moves_nothing():
    from django.core.management import call_command
    from djangocms_stories.cms_appconfig import StoriesConfig, config_defaults

    config = StoriesConfig.objects.create(namespace="on", **{**config_defaults, "use_placeholder": True})
    post = Post.objects.create(app_config=config)
    content = PostContent.admin_manager.create(
        post=post, title="Naujiena", slug="naujiena", language="lt", post_text="<p>Senas tekstas</p>"
    )

    call_command("migrate_post_text_to_placeholder", "--dry-run")

    content.refresh_from_db()
    assert content.post_text == "<p>Senas tekstas</p>"


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
