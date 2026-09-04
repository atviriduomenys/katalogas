from cms.models import Page, PageContent
from django import template
from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import get_language

register = template.Library()

MENU_CACHE_SECONDS = 60


def menu_cache_key(language: str) -> str:
    return f"navigation:menu:{language}"


def clear_menu_cache() -> None:
    cache.delete_many([menu_cache_key(code) for code, _ in settings.LANGUAGES])


def _published_nav_page_ids(language):
    """Return PKs of Pages that have published, in-navigation content.

    djangocms-versioning replaces `PageContent.objects` with a manager that
    returns published versions only, so drafts are already excluded here.

    The language filter matters because the rendered menu is cached per
    language: without it, a page published only in English would appear in the
    Lithuanian menu. distinct() stays because that manager joins to the version
    table.
    """
    return (
        PageContent.objects.filter(in_navigation=True, language=language).values_list("page_id", flat=True).distinct()
    )


def _render_menu(language: str) -> str:
    published_ids = _published_nav_page_ids(language)
    pages = Page.objects.filter(pk__in=published_ids, parent__isnull=True).order_by("path")
    return render_to_string(
        "menu.html",
        {
            # order_by: `children` is the plain reverse accessor and Page has no
            # default ordering, so without this the dropdown comes back in
            # database order - and show_menu then caches whichever order it got.
            "pages": {page: page.children.filter(pk__in=published_ids).order_by("path") for page in pages}
        },
    )


@register.simple_tag
def show_menu():
    key = menu_cache_key(get_language())
    html = cache.get(key)
    if html is None:
        html = _render_menu(get_language())
        cache.set(key, html, MENU_CACHE_SECONDS)
    return mark_safe(html)
