from cms.models import Page, PageContent
from django import template
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q, Count
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import get_language

from vitrina.orgs.models import Organization
from vitrina.settings import MORE_PAGE_REVERSE_ID, HELP_PAGE_REVERSE_ID, DATASET_PAGE_REVERSE_ID

register = template.Library()

MENU_CACHE_SECONDS = 60


def menu_cache_key(language: str) -> str:
    return f"navigation:menu:{language}"


def clear_menu_cache() -> None:
    cache.delete_many([menu_cache_key(code) for code, _ in settings.LANGUAGES])


def _published_nav_page_ids(language):
    """PKs of Pages with published, in-navigation content in this language.

    The menu is cached per language; distinct() as the versioning manager joins versions.
    """
    return (
        PageContent.objects.filter(in_navigation=True, language=language).values_list("page_id", flat=True).distinct()
    )


def _render_menu(language: str) -> str:
    published_ids = _published_nav_page_ids(language)
    pages = Page.objects.filter(pk__in=published_ids, parent__isnull=True).order_by("path")

    help_pages = pages.filter(Q(reverse_id=MORE_PAGE_REVERSE_ID) | Q(reverse_id=HELP_PAGE_REVERSE_ID))
    help_page_ids = set(help_pages.values_list("pk", flat=True))

    organization_count = Organization.public.count()
    organizations = Organization.public.annotate(
        dataset_count=Count(
            "dataset",
            filter=Q(dataset__search_doc__isnull=False),
        )
    ).order_by("-dataset_count")[:5]

    return render_to_string(
        "menu.html",
        {
            # Page has no default ordering, and show_menu caches whatever order it gets.
            "pages": {
                page: page.children.filter(pk__in=published_ids).order_by("path")
                for page in pages
                if page.pk not in help_page_ids
            },
            "help_pages": {page: page.children.filter(pk__in=published_ids).order_by("path") for page in help_pages},
            "organization_count": organization_count,
            "organizations": organizations,
            "dataset_page_reverse_id": DATASET_PAGE_REVERSE_ID,
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
