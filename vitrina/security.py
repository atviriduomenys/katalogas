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
    # ARIA attributes for accessibility (required by law for government sites)
    "*": [
        "aria-label",
        "aria-labelledby",
        "aria-describedby",
        "aria-hidden",
        "aria-live",
        "aria-atomic",
        "aria-relevant",
        "aria-busy",
        "aria-controls",
        "aria-haspopup",
        "aria-expanded",
        "aria-pressed",
        "aria-checked",
        "aria-selected",
        "aria-current",
    ],
}

# Allowed URL protocols
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def set_safe_link_attrs(attrs, new=False):
    """
    Callback for bleach.linkify to add security attributes to links.

    - nofollow: Prevent search engine following
    - noopener: Prevent window.opener access (security)
    - noreferrer: Don't send referrer header (privacy)

    Args:
        attrs: Dictionary of link attributes
        new: Whether this is a newly created link

    Returns:
        Updated attrs dictionary
    """
    attrs[(None, "rel")] = "nofollow noopener noreferrer"
    return attrs


def sanitize_html(html_content: str, strip: bool = False) -> str:
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
    # This adds rel="nofollow noopener noreferrer" to external links
    clean_html = bleach.linkify(
        clean_html,
        parse_email=True,
        callbacks=[set_safe_link_attrs],
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
