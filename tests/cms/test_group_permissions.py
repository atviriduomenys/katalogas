import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from vitrina.cms.apps import BLOG_ADMINISTRATORS, _sync_blog_administrator_permissions


def blog_era_permission(codename="change_post"):
    """A permission the way it looks on production: left over from djangocms_blog."""
    content_type, _ = ContentType.objects.get_or_create(app_label="djangocms_blog", model="post")
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type, codename=codename, defaults={"name": codename}
    )
    return permission


@pytest.mark.django_db
def test_migrations_leave_the_group_ready_to_use():
    # The receiver already ran while the test database was built.
    group = Group.objects.get(name=BLOG_ADMINISTRATORS)
    stories = Permission.objects.filter(content_type__app_label="djangocms_stories")

    assert stories.exists()
    assert set(group.permissions.values_list("pk", flat=True)) >= set(stories.values_list("pk", flat=True))


@pytest.mark.django_db
def test_blog_era_permissions_are_replaced():
    group = Group.objects.get(name=BLOG_ADMINISTRATORS)
    group.permissions.set([blog_era_permission()])

    _sync_blog_administrator_permissions(sender=None)

    assert not group.permissions.filter(content_type__app_label="djangocms_blog").exists()
    assert group.permissions.filter(content_type__app_label="djangocms_stories").exists()


@pytest.mark.django_db
def test_group_can_reach_the_story_admin():
    """The permissions the post admin in vitrina/cms/admin.py actually checks."""
    group = Group.objects.get(name=BLOG_ADMINISTRATORS)
    held = set(group.permissions.values_list("codename", flat=True))

    for codename in ("view_post", "add_post", "change_post", "delete_post", "change_postcontent"):
        assert codename in held


@pytest.mark.django_db
def test_running_again_changes_nothing():
    group = Group.objects.get(name=BLOG_ADMINISTRATORS)
    before = set(group.permissions.values_list("pk", flat=True))

    _sync_blog_administrator_permissions(sender=None)

    assert set(group.permissions.values_list("pk", flat=True)) == before


@pytest.mark.django_db
def test_missing_group_is_not_an_error():
    Group.objects.filter(name=BLOG_ADMINISTRATORS).delete()

    _sync_blog_administrator_permissions(sender=None)


@pytest.mark.django_db
def test_a_revoked_permission_stays_revoked():
    """The repair runs once. Re-granting on every migrate would undo an admin.

    Once the group carries stories permissions and no leftover blog ones, there
    is nothing left to repair, so a permission somebody deliberately took away
    must not come back with the next deployment.
    """
    group = Group.objects.get(name=BLOG_ADMINISTRATORS)
    revoked = group.permissions.get(codename="delete_post", content_type__app_label="djangocms_stories")
    group.permissions.remove(revoked)

    _sync_blog_administrator_permissions(sender=None)

    assert revoked not in group.permissions.all()
