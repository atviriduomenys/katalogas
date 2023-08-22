from cms.models import Page
from django import template

register = template.Library()


@register.inclusion_tag('menu.html')
def show_menu():
    published_pages = Page.objects.public().filter(in_navigation=True).values_list('pk', flat=True)
    pages = Page.objects.public().filter(
        in_navigation=True,
        node__parent__isnull=True
    ).order_by('node__path')
    return {
        'pages': {
            page: page.node.children.filter(cms_pages__pk__in=published_pages)
            for page in pages
        }
    }
