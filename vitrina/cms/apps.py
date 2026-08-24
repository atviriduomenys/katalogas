from django.apps import AppConfig
from django.db import transaction
from django.db.models.signals import post_delete, post_migrate, post_save

BLOG_ADMINISTRATORS = "Blog Administrators"


class CmsConfig(AppConfig):
    name = "vitrina.cms"
    label = "vitrina_cms"

    def ready(self):
        from cms.models import Page, PageContent
        from djangocms_versioning.signals import post_version_operation

        from vitrina.templatetags.navigation_tags import clear_menu_cache

        def _clear(sender, **kwargs):
            transaction.on_commit(clear_menu_cache)

        post_save.connect(_clear, sender=Page, dispatch_uid="vitrina_cms.clear_menu_cache")
        post_delete.connect(_clear, sender=Page, dispatch_uid="vitrina_cms.clear_menu_cache")
        # Publishing and unpublishing are what change the menu now, and neither
        # writes to Page - the state lives on the version of the page content,
        # so the two signals above never fire for it.
        post_version_operation.connect(
            _clear,
            sender=PageContent,
            dispatch_uid="vitrina_cms.clear_menu_cache_on_version_operation",
        )
        self._clear_menu_cache = _clear

        post_save.connect(_add_default_text_plugin, sender="djangocms_stories.PostContent")
        post_migrate.connect(_sync_blog_administrator_permissions, sender=self)


def _add_default_text_plugin(sender, instance, created, **kwargs):
    if not created or not instance.content:
        return
    from cms.api import add_plugin
    from cms.models import CMSPlugin

    if not CMSPlugin.objects.filter(placeholder=instance.content).exists():
        add_plugin(instance.content, "TextPlugin", instance.language, body="<Vieta Jūsų tekstui.>")


def _sync_blog_administrator_permissions(sender, **kwargs):
    """Point the Blog Administrators group at the djangocms_stories permissions.

    `vitrina/users/migrations/0003` fills this group by reading the permissions
    of the blog app. A migration cannot get this right: permissions for a
    model are created by `post_migrate`, once every migration has run, so at
    the time 0003 executes there is nothing to read. On a fresh database the
    group therefore comes out empty, and on production it is still holding the
    24 djangocms_blog permissions 0003 gave it back when that app existed -
    dead rows now that `vitrina/cms/admin.py` asks for djangocms_stories ones.

    This runs after every migrate and is a no-op once the group is in order.
    django.contrib.auth creates permissions on the same signal, and
    djangocms_stories is listed before vitrina.cms in INSTALLED_APPS, so its
    permissions are already in place by the time this fires.

    The other group 0003 creates, CMS Administrators, needs no such repair: its
    four cms.title permissions have no successor, because PageContent declares
    `default_permissions = []`. Its page permissions survive the upgrade
    untouched.
    """
    from django.contrib.auth.models import Group, Permission

    group = Group.objects.filter(name=BLOG_ADMINISTRATORS).first()
    if group is None:
        return

    missing = Permission.objects.filter(content_type__app_label="djangocms_stories").exclude(
        pk__in=group.permissions.values("pk")
    )
    if missing:
        group.permissions.add(*missing)

    stale = group.permissions.filter(content_type__app_label="djangocms_blog")
    if stale:
        group.permissions.remove(*stale)
