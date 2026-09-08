import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory
from djangocms_stories.cms_appconfig import StoriesConfig, config_defaults
from djangocms_stories.models import Post, PostContent

from djangocms_versioning.models import Version

from vitrina.cms.models import FileResource
from vitrina.cms.views import PostDetailView
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_attachments_are_found_through_the_post_not_its_content():
    """Attachments hang off the post; the view's object is the post's content.

    The one-off news import stored every attachment against the post itself. A lookup keyed on the content object asks for a different content
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
