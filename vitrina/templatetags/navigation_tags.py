from cms.models import Page, PageContent
from django import template

register = template.Library()


@register.inclusion_tag("menu.html")
def show_menu():
    # Django-CMS 4.x: publisher_is_draft field removed, in_navigation moved to PageContent
    # In CMS 4.x, if page exists it's considered active/published

    # Get page IDs that are in navigation
    page_ids_in_nav = PageContent.objects.filter(in_navigation=True).values_list("page_id", flat=True).distinct()

    # Get root pages that are in navigation
    pages = Page.objects.filter(pk__in=page_ids_in_nav, node__parent__isnull=True).order_by("node__path")

    return {"pages": {page: page.node.children.filter(cms_pages__pk__in=page_ids_in_nav) for page in pages}}
