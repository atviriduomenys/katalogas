"""
Test suite for comments XSS vulnerability fix.

Tests that user comments are properly sanitized to prevent XSS attacks
while preserving safe markdown formatting.
"""

import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.comments.models import Comment
from vitrina.datasets.models import Dataset
from vitrina.templatetags.markdown_tags import markdown
from vitrina.users.models import Representative


# XSS payloads to test
XSS_PAYLOADS = [
    # Basic script injection
    '<script>alert("XSS")</script>',
    "<script>alert(String.fromCharCode(88,83,83))</script>",
    # Image onerror
    '<img src=x onerror="alert(1)">',
    "<img src=x onerror=\"window.location='http://attacker.com'\">",
    # SVG injection
    '<svg onload="alert(1)">',
    "<svg><script>alert(1)</script></svg>",
    # JavaScript URLs
    '<a href="javascript:alert(1)">Click</a>',
    "[Link](javascript:alert(1))",  # Markdown format
    # Event handlers
    '<div onmouseover="alert(1)">Hover me</div>',
    '<input onfocus="alert(1)" autofocus>',
    '<body onload="alert(1)">',
    # Iframe injection
    '<iframe src="javascript:alert(1)">',
    '<iframe src="data:text/html,<script>alert(1)</script>">',
]


@pytest.mark.django_db
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_comment_blocks_xss_payload(user, dataset, payload):
    """Test that comments block all XSS payloads."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(user=user, body=payload, type=Comment.USER, content_type=ct, object_id=dataset.id)

    # Get rendered HTML (simulating template rendering)
    body = comment.body_text()
    html = markdown(body)
    html_lower = str(html).lower()

    # Dangerous content should be escaped (not executable)
    # Check that we don't have UNESCAPED dangerous tags
    assert "<script>" not in html_lower, f"Unescaped script tag found in: {html}"
    assert "<script " not in html_lower, f"Unescaped script tag found in: {html}"
    assert "<iframe " not in html_lower, f"Unescaped iframe found in: {html}"
    assert "<iframe>" not in html_lower, f"Unescaped iframe found in: {html}"

    # Event handlers should not be on real HTML tags
    # If they appear, they should be in escaped text (harmless)
    if "onerror=" in html_lower and "<img " in html_lower:
        # Make sure the img tag with onerror is escaped
        assert "&lt;img" in html or "<p>&lt;" in html, f"Unescaped img onerror found: {html}"
    if "onload=" in html_lower and ("<svg" in html_lower or "<body" in html_lower):
        # Make sure svg/body with onload is escaped
        assert "&lt;svg" in html or "&lt;body" in html, f"Unescaped onload found: {html}"


@pytest.mark.django_db
def test_comment_preserves_safe_markdown(user, dataset):
    """Test that safe markdown formatting is preserved."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(
        user=user,
        body="**Bold** and *italic* and [link](https://example.com)",
        type=Comment.USER,
        content_type=ct,
        object_id=dataset.id,
    )

    # Render markdown as in template
    body = comment.body_text()
    html = str(markdown(body))

    # Should contain safe HTML
    assert "<strong>Bold</strong>" in html or "<b>Bold</b>" in html
    assert "<em>italic</em>" in html or "<i>italic</i>" in html
    assert 'href="https://example.com"' in html


@pytest.mark.django_db
def test_comment_mixed_safe_and_malicious(user, dataset):
    """Test comment with mixed safe and malicious content."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(
        user=user,
        body="""
This is **safe** content.

<script>alert("XSS")</script>

And more *safe* content.
        """,
        type=Comment.USER,
        content_type=ct,
        object_id=dataset.id,
    )

    # Render markdown as in template
    body = comment.body_text()
    html = str(markdown(body))

    # Safe content preserved
    assert "<strong>safe</strong>" in html or "<b>safe</b>" in html

    # Malicious content escaped (not executable)
    assert "<script>" not in html.lower()
    assert "<script " not in html.lower()
    # The word 'alert' might appear in escaped text, which is safe
    # Check that script tags specifically are escaped
    if "script" in html.lower():
        assert "&lt;script" in html, f"Script tag not escaped: {html}"


@pytest.mark.django_db
def test_comment_empty_body(user, dataset):
    """Test comment with empty body."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(user=user, body="", type=Comment.USER, content_type=ct, object_id=dataset.id)

    html = comment.body_text()
    # Should handle empty gracefully
    assert html == "" or html is None or str(html) == ""


@pytest.mark.django_db
def test_comment_code_blocks(user, dataset):
    """Test that markdown code blocks work safely."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(
        user=user,
        body='Here is some code:\n\n```python\nprint("hello")\n```',
        type=Comment.USER,
        content_type=ct,
        object_id=dataset.id,
    )

    # Render markdown as in template
    body = comment.body_text()
    html = str(markdown(body))

    # Should contain code block
    assert "<code>" in html or "<pre>" in html
    # But no script execution
    assert "<script" not in html.lower()


@pytest.mark.django_db
def test_comment_parent_xss_protection(user, dataset):
    """Test that comment parent preview sanitizes XSS payloads."""
    from django.template import Template, Context

    ct = ContentType.objects.get_for_model(dataset)

    # Create parent comment with XSS payload
    parent = Comment.objects.create(
        user=user, body="<script>alert(1)</script>Test", type=Comment.USER, content_type=ct, object_id=dataset.id
    )

    # Create reply
    reply = Comment.objects.create(
        user=user, body="Reply text", type=Comment.USER, content_type=ct, object_id=dataset.id, parent=parent
    )

    # Render the parent preview template snippet (as in comment.html)
    template = Template("{% load markdown_tags %}{{ comment.parent.body_text|markdown|truncatechars:20 }}")
    context = Context({"comment": reply})
    html = template.render(context)

    # Check XSS is escaped/removed
    assert "<script>" not in html, "Unescaped script tag in parent preview"
    assert "alert(" not in html.lower() or "&lt;script&gt;" in html

    # Should be truncated
    assert "…" in html or len(html) < 50, "Parent preview not truncated"


@pytest.mark.django_db
def test_comment_preserves_aria_attributes(user, dataset):
    """Test that ARIA attributes are preserved for accessibility."""
    ct = ContentType.objects.get_for_model(dataset)

    # Create comment with ARIA attributes in markdown/HTML
    comment_body = '<a href="https://example.com" aria-label="External link to example">Link</a>'

    comment = Comment.objects.create(
        user=user, body=comment_body, type=Comment.USER, content_type=ct, object_id=dataset.id
    )

    # Render through markdown filter
    body = comment.body_text()
    html = str(markdown(body))

    # Check ARIA attribute preserved
    assert "aria-label" in html, "ARIA attribute was stripped by sanitization"
    assert "External link" in html or "example" in html


def test_sanitize_html_adds_safe_link_attributes():
    """Test that links get security attributes."""
    from vitrina.security import sanitize_html

    html = '<a href="https://example.com">Link</a>'
    result = sanitize_html(html)

    # Should have security attributes
    assert 'rel="nofollow noopener noreferrer"' in result
    assert 'href="https://example.com"' in result


def test_sanitize_html_preserves_aria():
    """Test that sanitize_html preserves ARIA attributes."""
    from vitrina.security import sanitize_html

    html = '<button aria-label="Close dialog" aria-pressed="false">Close</button>'
    result = sanitize_html(html)

    # ARIA attributes should be preserved
    # Note: <button> might be stripped, but let's test with allowed tag
    html = '<a href="#" aria-label="Navigation link" aria-current="page">Link</a>'
    result = sanitize_html(html)

    assert "aria-label" in result
    assert "aria-current" in result

@pytest.mark.parametrize(
    "role",
    [
        Representative.OPEN_DATA_COORDINATOR,
        Representative.RESOURCE_COORDINATOR,
    ],
)
@pytest.mark.django_db
def test_comment_xss_end_to_end_protection(client, user, organization, dataset, role: Representative):
    """
    End-to-end test: Post comment with XSS payload, verify it's sanitized in rendered page.
    """
    from django.urls import reverse
    from vitrina.orgs.models import Representative

    # Make dataset public and give user permission to comment
    dataset.is_public = True
    dataset.access_rights = Dataset.PUBLIC
    dataset.save()

    # Add user as representative to have permission
    Representative.objects.create(
        content_object=organization,
        user=user,
        role=role,
    )

    # Login user
    client.force_login(user)

    # Prepare XSS payload with safe markdown
    xss_payload = '<script>alert("XSS")</script>**Bold** text with [link](http://example.com)'

    # Post comment
    content_type = ContentType.objects.get_for_model(dataset)
    post_url = reverse("comment", kwargs={"content_type_id": content_type.pk, "object_id": dataset.pk})

    response = client.post(
        post_url,
        {
            "body": xss_payload,
            "is_public": True,
        },
    )

    # Should redirect to dataset detail page
    assert response.status_code == 302, f"Expected redirect, got {response.status_code}"

    # Get page where comment is displayed
    detail_url = dataset.get_absolute_url()
    response = client.get(detail_url, follow=True)

    assert response.status_code == 200, f"Dataset detail returned {response.status_code}"

    # Verify XSS is blocked
    content = response.content.decode("utf-8")
    assert "<script>" not in content, "Unescaped script tag in response"
    # Check for escaped version or complete removal
    if "alert" in content.lower():
        assert "&lt;script&gt;" in content, "Script not properly escaped"

    # Verify safe content is rendered (markdown converted to HTML)
    assert "<strong>Bold</strong>" in content or "<b>Bold</b>" in content, "Safe markdown not rendered"
    assert 'href="http://example.com"' in content, "Safe link not rendered"
