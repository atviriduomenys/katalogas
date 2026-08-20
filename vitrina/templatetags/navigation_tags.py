from cms.models import Page
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


def _render_menu() -> str:
    published_pages = Page.objects.public().filter(in_navigation=True).values_list("pk", flat=True)
    pages = Page.objects.public().filter(in_navigation=True, node__parent__isnull=True).order_by("node__path")
    return render_to_string(
        "menu.html",
        {"pages": {page: page.node.children.filter(cms_pages__pk__in=published_pages) for page in pages}},
    )


@register.simple_tag
def show_menu():
    key = menu_cache_key(get_language())
    html = cache.get(key)
    if html is None:
        html = _render_menu()
        cache.set(key, html, MENU_CACHE_SECONDS)
    return mark_safe(html)
