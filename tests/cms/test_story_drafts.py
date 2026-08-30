import pytest
from cms.api import add_plugin
from cms.models import CMSPlugin
from djangocms_stories.cms_appconfig import StoriesConfig, config_defaults
from djangocms_stories.models import Post, PostContent
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.models import Version

from vitrina.users.factories import UserFactory

DEFAULT_TEXT = "<p>Vieta Jūsų tekstui.</p>"


def make_published_story(user, body="<p>Tikras tekstas</p>"):
    config = StoriesConfig.objects.create(namespace="stories", **config_defaults)
    post = Post.objects.create(app_config=config)
    content = PostContent.admin_manager.create(post=post, title="Naujiena", slug="naujiena", language="lt")

    CMSPlugin.objects.filter(placeholder=content.content).delete()
    add_plugin(content.content, "TextPlugin", "lt", body=body)

    version = Version.objects.create(content=content, created_by=user, state=DRAFT)
    version.publish(user)
    return version


@pytest.mark.django_db
def test_a_new_story_gets_the_editor_hint():
    config = StoriesConfig.objects.create(namespace="stories", **config_defaults)
    post = Post.objects.create(app_config=config)

    content = PostContent.admin_manager.create(post=post, title="Naujiena", slug="naujiena", language="lt")

    plugins = CMSPlugin.objects.filter(placeholder=content.content)
    assert [p.get_plugin_instance()[0].body for p in plugins] == [DEFAULT_TEXT]


@pytest.mark.django_db
def test_editing_a_published_story_keeps_the_article():
    """Versioning copies the content row first and its placeholders after.

    A receiver that reaches for the placeholder in between creates a second
    one, and that empty one wins - the editor opens the draft and finds the
    hint text where the article should be.
    """
    user = UserFactory()
    version = make_published_story(user)

    draft = version.copy(user).content

    assert draft.placeholders.count() == 1
    plugins = CMSPlugin.objects.filter(placeholder=draft.content)
    assert [p.get_plugin_instance()[0].body for p in plugins] == ["<p>Tikras tekstas</p>"]
