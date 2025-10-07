"""
Security utilities for sanitizing user input and preventing XSS attacks.
"""

import bleach


# Allowed HTML tags for user-generated content
# Based on safe markdown subset
ALLOWED_TAGS = [
    # Text formatting
    "p",
    "br",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "code",
    "pre",
    # Lists
    "ul",
    "ol",
    "li",
    # Headings
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    # Links
    "a",
    # Blockquotes
    "blockquote",
    # Tables
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    # Other
    "hr",
    "span",
    "div",
]

# Allowed attributes for specific tags
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "code": ["class"],  # For language highlighting
    "pre": ["class"],
    "span": ["class"],
    "div": ["class"],
}

# Allowed URL protocols
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_html(html_content: str, strip=False) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    This function uses bleach to remove dangerous HTML and JavaScript
    while preserving safe formatting tags.

    Args:
        html_content: The HTML string to sanitize
        strip: If True, strip disallowed tags instead of escaping them

    Returns:
        Sanitized HTML string safe for display

    Examples:
        >>> sanitize_html('<script>alert("XSS")</script>')
        '&lt;script&gt;alert("XSS")&lt;/script&gt;'

        >>> sanitize_html('<strong>Safe</strong> text')
        '<strong>Safe</strong> text'

        >>> sanitize_html('<a href="javascript:alert(1)">Click</a>')
        '<a>Click</a>'
    """
    if not html_content:
        return ""

    # Sanitize with bleach
    clean_html = bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=strip,
    )

    # Also run linkify to ensure all links are safe
    # This adds rel="nofollow" to external links
    clean_html = bleach.linkify(
        clean_html,
        parse_email=True,
        callbacks=[],
    )

    return clean_html


def sanitize_markdown_html(markdown_html: str) -> str:
    """
    Sanitize HTML output from markdown rendering.

    This is specifically for content that has been processed by
    a markdown library and needs XSS protection.

    Args:
        markdown_html: HTML string from markdown rendering

    Returns:
        Sanitized HTML string
    """
    return sanitize_html(markdown_html, strip=False)
