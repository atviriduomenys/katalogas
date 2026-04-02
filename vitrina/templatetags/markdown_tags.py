from django import template
from django.template.defaultfilters import stringfilter

import markdown as md

from vitrina.security import sanitize_markdown_html

register = template.Library()


@register.filter()
@stringfilter
def markdown(value):
    """
    Convert Markdown to HTML and sanitize for XSS protection.

    This filter processes Markdown and ensures the output is safe
    by removing any malicious scripts or HTML.
    """
    # Convert Markdown to HTML
    html = md.markdown(value, extensions=["markdown.extensions.fenced_code"])

    # Sanitize the HTML to prevent XSS
    return sanitize_markdown_html(html)
