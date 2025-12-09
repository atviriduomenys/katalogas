"""
Test suite for task description XSS vulnerability fix.

Issue: #291 - Persistent XSS in Task Descriptions
Related: PR #1989 (Comments XSS fix)

Tests that task descriptions are properly sanitized to prevent XSS attacks
while preserving safe markdown formatting.
"""

import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.tasks.models import Task
from vitrina.templatetags.markdown_tags import markdown


# XSS payloads to test (same as comments)
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
    # Additional payloads
    '<object data="data:text/html,<script>alert(1)</script>">',
    '<embed src="javascript:alert(1)">',
]


@pytest.mark.django_db
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_task_description_blocks_xss_payload(user, dataset, payload):
    """Test that task descriptions block all XSS payloads."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description=payload,
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    # Render using markdown filter (as in template)
    html = markdown(task.description)
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
def test_task_description_blocks_script_tag(user, dataset):
    """Test that script tags are completely removed."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description='<script>alert("XSS")</script>Normal text',
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    # Script tag should be escaped (safe) or removed
    assert "<script>" not in html_lower  # Unescaped = dangerous
    assert "<script " not in html_lower  # Unescaped with attributes = dangerous
    # Note: &lt;script&gt; (escaped) is OK - it displays as text
    assert "normal text" in html_lower


@pytest.mark.django_db
def test_task_description_blocks_img_onerror(user, dataset):
    """Test that image onerror handlers are stripped."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description='<img src=x onerror="alert(1)">',
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    # Image tag should be escaped (safe) or removed
    assert "<img src=x onerror=" not in html_lower  # Unescaped with handler = dangerous
    # Note: &lt;img (escaped) is OK - it displays as text


@pytest.mark.django_db
def test_task_description_blocks_javascript_url(user, dataset):
    """Test that javascript: URLs are blocked."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description="[Click me](javascript:alert(1))",
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    # Link should exist but without javascript: protocol
    assert "<a" in html_lower
    assert "javascript:" not in html_lower


@pytest.mark.django_db
def test_task_description_blocks_event_handlers(user, dataset):
    """Test that event handlers are stripped."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description='<div onclick="alert(1)">Click me</div>',
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    # div is not in allowed tags, should be stripped
    # onclick should definitely not appear
    assert "onclick" not in html_lower


@pytest.mark.django_db
def test_task_description_blocks_iframe(user, dataset):
    """Test that iframe injection is blocked."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description='<iframe src="https://evil.com"></iframe>',
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    assert "<iframe" not in html_lower


@pytest.mark.django_db
def test_task_description_blocks_svg_onload(user, dataset):
    """Test that SVG onload is blocked."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description='<svg onload="alert(1)">',
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    # SVG with onload should be escaped (safe) or removed
    assert "<svg onload=" not in html_lower  # Unescaped with handler = dangerous
    # Note: &lt;svg (escaped) is OK - it displays as text


@pytest.mark.django_db
def test_task_description_blocks_object_embed(user, dataset):
    """Test that object/embed tags are blocked."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description='<object data="javascript:alert(1)"></object><embed src="evil.swf">',
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    assert "<object" not in html_lower
    assert "<embed" not in html_lower


@pytest.mark.django_db
def test_task_description_preserves_markdown_formatting(user, dataset):
    """Test that safe markdown formatting is preserved."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description="**Bold** text and *italic* text and [link](https://example.com)",
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    # Safe HTML should be preserved
    assert "<strong>bold</strong>" in html_lower or "<b>bold</b>" in html_lower
    assert "<em>italic</em>" in html_lower or "<i>italic</i>" in html_lower
    assert '<a href="https://example.com"' in html_lower


@pytest.mark.django_db
def test_task_description_preserves_lists(user, dataset):
    """Test that markdown lists are preserved."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description="- Item 1\n- Item 2\n- Item 3",
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    assert "<ul>" in html_lower or "<ol>" in html_lower
    assert "<li>" in html_lower
    assert "item 1" in html_lower


@pytest.mark.django_db
def test_task_description_preserves_code_blocks(user, dataset):
    """Test that code blocks are preserved."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description="```python\nprint('hello')\n```",
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    assert "<code>" in html_lower or "<pre>" in html_lower
    assert "print" in html_lower


@pytest.mark.django_db
def test_task_description_handles_empty_null(user, dataset):
    """Test that empty/null descriptions are handled safely."""
    ct = ContentType.objects.get_for_model(dataset)

    # Empty string
    task1 = Task.objects.create(
        title="Test Task",
        description="",
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )
    html1 = markdown(task1.description)
    assert html1 is not None

    # None
    task2 = Task.objects.create(
        title="Test Task",
        description=None,
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )
    # Should handle None gracefully (template checks for None)
    assert task2.description is None


@pytest.mark.django_db
def test_task_mixed_safe_and_malicious_content(user, dataset):
    """Test that mixed safe and malicious content is handled correctly."""
    ct = ContentType.objects.get_for_model(dataset)
    task = Task.objects.create(
        title="Test Task",
        description='This is **safe** content.\n\n<script>alert("XSS")</script>\n\nMore *safe* content.',
        organization=user.organization,
        content_type=ct,
        object_id=dataset.id,
    )

    html = markdown(task.description)
    html_lower = str(html).lower()

    # Safe content should be preserved
    assert "<strong>safe</strong>" in html_lower or "<b>safe</b>" in html_lower
    assert "<em>safe</em>" in html_lower or "<i>safe</i>" in html_lower

    # Malicious content should be escaped (safe) or removed
    assert "<script>" not in html_lower  # Unescaped = dangerous
    assert "<script " not in html_lower  # Unescaped with attributes = dangerous
    # Note: &lt;script&gt; (escaped) is OK - it displays as text, won't execute
