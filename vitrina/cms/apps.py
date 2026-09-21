from django.apps import AppConfig
from django.db import transaction
from django.db.models.signals import post_delete, post_migrate, post_save

BLOG_ADMINISTRATORS = "Blog Administrators"


class CmsConfig(AppConfig):
    name = "vitrina.cms"
    label = "vitrina_cms"

    def ready(self):
        # apps.py is imported before the app registry is ready, so every import
        # that reaches a model has to sit inside a function - here and below.
        from cms.models import Page, PageContent
        from djangocms_versioning.signals import post_version_operation

        from vitrina.templatetags.navigation_tags import clear_menu_cache

        def _clear(sender, **kwargs):
            transaction.on_commit(clear_menu_cache)

        post_save.connect(_clear, sender=Page, dispatch_uid="vitrina_cms.clear_menu_cache")
        post_delete.connect(_clear, sender=Page, dispatch_uid="vitrina_cms.clear_menu_cache")
        # Publishing does not write to Page - the state lives on the page content's
        # version - so the two signals above never fire for it.
        post_version_operation.connect(
            _clear,
            sender=PageContent,
            dispatch_uid="vitrina_cms.clear_menu_cache_on_version_operation",
        )
        self._clear_menu_cache = _clear

        post_save.connect(_add_default_text_plugin, sender="djangocms_stories.PostContent")
        post_migrate.connect(_sync_blog_administrator_permissions, sender=self)


def _add_default_text_plugin(sender, instance, created, **kwargs):
    """Put a hint in the editor when a story is first written.

    Skipped for a new draft of an existing story: its placeholders are copied after this runs.
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

    # With placeholders off the hint is never shown, only left behind.
    config = instance.post.app_config if instance.post_id else None
    if not (config and config.use_placeholder):
        return

    placeholder = instance.content
    if not placeholder:
        return

    if not CMSPlugin.objects.filter(placeholder=placeholder).exists():
        add_plugin(placeholder, "TextPlugin", instance.language, body="<p>Vieta Jūsų tekstui.</p>")


def _sync_blog_administrator_permissions(sender, **kwargs):
    """Swap the Blog Administrators group's djangocms_blog permissions for djangocms_stories ones.

    Migration 0003 can't: permissions only exist after post_migrate, which this listens to.
    """
    from django.contrib.auth.models import Group, Permission

    group = Group.objects.filter(name=BLOG_ADMINISTRATORS).first()
    if group is None:
        return

    stale = group.permissions.filter(content_type__app_label="djangocms_blog")
    granted = group.permissions.filter(content_type__app_label="djangocms_stories")

    # Repair once: re-granting on every migrate would undo an administrator's change.
    if granted.exists() and not stale.exists():
        return

    missing = Permission.objects.filter(content_type__app_label="djangocms_stories").exclude(
        pk__in=group.permissions.values("pk")
    )
    if missing:
        group.permissions.add(*missing)
    if stale:
        group.permissions.remove(*stale)
