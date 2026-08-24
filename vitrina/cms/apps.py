from django.apps import AppConfig
from django.db import transaction
from django.db.models.signals import post_delete, post_save


class CmsConfig(AppConfig):
    name = "vitrina.cms"
    label = "vitrina_cms"

    def ready(self):
        from cms.models import Page

        from vitrina.templatetags.navigation_tags import clear_menu_cache

        def _clear(sender, **kwargs):
            transaction.on_commit(clear_menu_cache)

        post_save.connect(_clear, sender=Page, dispatch_uid="vitrina_cms.clear_menu_cache")
        post_delete.connect(_clear, sender=Page, dispatch_uid="vitrina_cms.clear_menu_cache")
        self._clear_menu_cache = _clear
