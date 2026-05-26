from cms.models import Page, PageContent
from django import template
from djangocms_versioning.constants import PUBLISHED

register = template.Library()

def _published_nav_page_ids():
    """Return PKs of Pages that have a published PageContent with in_navigation=True."""
    return (
        PageContent.objects.filter(in_navigation=True, versions__state=PUBLISHED)
        .values_list("page_id", flat=True)
    )

def _published_nav_page_ids():
    """Return PKs of Pages that have a published PageContent with in_navigation=True."""
    return PageContent.objects.filter(in_navigation=True, versions__state=PUBLISHED).values_list("page_id", flat=True)


@register.inclusion_tag("menu.html")
def show_menu():
    published_ids = _published_nav_page_ids()
    pages = Page.objects.filter(pk__in=published_ids, parent__isnull=True).order_by("path")
    return {"pages": {page: page.children.filter(pk__in=published_ids) for page in pages}}
