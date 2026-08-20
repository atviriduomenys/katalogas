from cms.models import Page, PageContent
from django import template

register = template.Library()


def _published_nav_page_ids():
    """Return PKs of Pages that have published, in-navigation content.

    djangocms-versioning replaces `PageContent.objects` with a manager that
    returns published versions only, so drafts are already excluded here. That
    manager joins to the version table, and there is one PageContent per
    language, so the same page id comes back more than once - hence distinct().
    """
    return PageContent.objects.filter(in_navigation=True).values_list("page_id", flat=True).distinct()


@register.inclusion_tag("menu.html")
def show_menu():
    published_ids = _published_nav_page_ids()
    pages = Page.objects.filter(pk__in=published_ids, parent__isnull=True).order_by("path")
    return {"pages": {page: page.children.filter(pk__in=published_ids) for page in pages}}
