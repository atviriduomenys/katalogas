from django.apps import AppConfig, apps
from django.db import transaction
from django.db import connections
from django.db.models.signals import post_delete, post_migrate, post_save, pre_migrate

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
        # Once per migrate, before anything is applied: pre_migrate is sent per app,
        # and cms is the app whose migrations would do the damage.
        pre_migrate.connect(
            _refuse_cms3_schema,
            sender=apps.get_app_config("cms"),
            dispatch_uid="vitrina_cms.refuse_cms3_schema",
        )


def _add_default_text_plugin(sender, instance, created, **kwargs):
    """Put a hint in the editor when a story is written for the first time.

    Only then. Versioning makes a draft out of a published story by creating a
    new content row and copying the placeholders afterwards, and this receiver
    runs in between. Reading `instance.content` at that moment creates a second
    "content" placeholder, which then wins over the copied one - the editor
    opens the draft, finds this boilerplate instead of the article, and
    publishing it would put the boilerplate on the site. So leave alone any
    content that already has a sibling in the same language.
    """
    if not created:
        return

    from cms.api import add_plugin
    from cms.models import CMSPlugin
    from djangocms_stories.models import PostContent

    siblings = PostContent.admin_manager.filter(
        post_id=instance.post_id,
        language=instance.language,
    ).exclude(pk=instance.pk)
    if siblings.exists():
        return

    # With placeholders off the article is rendered from post_text and this hint
    # is never shown, so writing it only leaves an unused placeholder behind.
    config = instance.post.app_config if instance.post_id else None
    if not (config and config.use_placeholder):
        return

    placeholder = instance.content
    if not placeholder:
        return

    if not CMSPlugin.objects.filter(placeholder=placeholder).exists():
        add_plugin(placeholder, "TextPlugin", instance.language, body="<p>Vieta Jūsų tekstui.</p>")


def _sync_blog_administrator_permissions(sender, **kwargs):
    """Fill the Blog Administrators group with the djangocms_stories permissions.

    `vitrina/users/migrations/0003` fills this group by reading the permissions
    of the blog app. A migration cannot get this right: permissions for a
    model are created by `post_migrate`, once every migration has run, so at
    the time 0003 executes there is nothing to read, and on a fresh database
    the group comes out empty.

    This runs after every migrate. It returns as soon as the group has any
    djangocms_stories permission - deliberately not the full set, so a permission
    an administrator has since taken away stays away.
    django.contrib.auth creates permissions on the same signal, and
    djangocms_stories is listed before vitrina.cms in INSTALLED_APPS, so its
    permissions are already in place by the time this fires.

    The other group 0003 creates, CMS Administrators, needs nothing: its four
    cms.title permissions have no successor, because PageContent declares
    `default_permissions = []`, and its page permissions stand on their own.
    """
    from django.contrib.auth.models import Group, Permission

    group = Group.objects.filter(name=BLOG_ADMINISTRATORS).first()
    if group is None:
        return

    # Fill once, then leave the group alone. Re-granting the whole set on every
    # migrate would undo any permission an administrator has since taken away.
    if group.permissions.filter(content_type__app_label="djangocms_stories").exists():
        return

    missing = Permission.objects.filter(content_type__app_label="djangocms_stories").exclude(
        pk__in=group.permissions.values("pk")
    )
    if missing:
        group.permissions.add(*missing)


# cms.0032 renamed Title to PageContent, so a database that still has cms_title is
# on the django-cms 3 schema.
LEGACY_PAGE_TABLE = "cms_title"


def _refuse_cms3_schema(sender, using="default", **kwargs):
    """Stop migrate before it touches a django-cms 3 database.

    django-cms 5's migrations would take such a page tree past the point where the
    3 -> 4 conversion can still run, and there is no way back but a backup. The
    one-time upgrade is over, but the case outlives it: restore a backup from before
    the upgrade into an environment already on cms 5, forget to roll the image back
    with it, and the next start - or a migrate run by hand - would do exactly that.

    What stays of the upgrade's own checks after #2795 removed the rest; it costs
    one query per migrate.
    """
    from django.core.management.base import CommandError

    if LEGACY_PAGE_TABLE in connections[using].introspection.table_names():
        raise CommandError(
            f"This database still has {LEGACY_PAGE_TABLE}: its page tree is on the django-cms 3 schema. "
            "Migrating it with django-cms 5 would take it past the point where the 3 -> 4 conversion can "
            "still run. Roll back to the release that matches it, or convert it first - the procedure is "
            "in git history: git log -- notes/migrations/djangocms/diegimas.md. Refusing."
        )
