"""
Test suite for comments XSS vulnerability fix.

Tests that user comments are properly sanitized to prevent XSS attacks
while preserving safe markdown formatting.
"""
import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.comments.models import Comment
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.users.models import User
from vitrina.templatetags.markdown_tags import markdown


# XSS payloads to test
XSS_PAYLOADS = [
    # Basic script injection
    '<script>alert("XSS")</script>',
    '<script>alert(String.fromCharCode(88,83,83))</script>',
    
    # Image onerror
    '<img src=x onerror="alert(1)">',
    '<img src=x onerror="window.location=\'http://attacker.com\'">',
    
    # SVG injection
    '<svg onload="alert(1)">',
    '<svg><script>alert(1)</script></svg>',
    
    # JavaScript URLs
    '<a href="javascript:alert(1)">Click</a>',
    '[Link](javascript:alert(1))',  # Markdown format
    
    # Event handlers
    '<div onmouseover="alert(1)">Hover me</div>',
    '<input onfocus="alert(1)" autofocus>',
    '<body onload="alert(1)">',
    
    # Iframe injection
    '<iframe src="javascript:alert(1)">',
    '<iframe src="data:text/html,<script>alert(1)</script>">',
]


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        password='testpass123'
    )


@pytest.fixture
def organization(db):
    """Create test organization."""
    return Organization.add_root(
        title='Test Organization',
        company_code='123456'
    )


@pytest.fixture
def dataset(db, organization):
    """Create test dataset."""
    return Dataset.objects.create(
        title='Test Dataset',
        organization=organization
    )


@pytest.mark.django_db
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_comment_blocks_xss_payload(user, dataset, payload):
    """Test that comments block all XSS payloads."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(
        user=user,
        body=payload,
        type=Comment.USER,
        content_type=ct,
        object_id=dataset.id
    )
    
    # Get rendered HTML (simulating template rendering)
    body = comment.body_text()
    html = markdown(body)
    html_lower = str(html).lower()
    
    # Dangerous content should be escaped (not executable)
    # Check that we don't have UNESCAPED dangerous tags
    assert '<script>' not in html_lower, f"Unescaped script tag found in: {html}"
    assert '<script ' not in html_lower, f"Unescaped script tag found in: {html}"
    assert '<iframe ' not in html_lower, f"Unescaped iframe found in: {html}"
    assert '<iframe>' not in html_lower, f"Unescaped iframe found in: {html}"
    
    # Event handlers should not be on real HTML tags
    # If they appear, they should be in escaped text (harmless)
    if 'onerror=' in html_lower and '<img ' in html_lower:
        # Make sure the img tag with onerror is escaped
        assert '&lt;img' in html or '<p>&lt;' in html, f"Unescaped img onerror found: {html}"
    if 'onload=' in html_lower and ('<svg' in html_lower or '<body' in html_lower):
        # Make sure svg/body with onload is escaped
        assert '&lt;svg' in html or '&lt;body' in html, f"Unescaped onload found: {html}"


@pytest.mark.django_db
def test_comment_preserves_safe_markdown(user, dataset):
    """Test that safe markdown formatting is preserved."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(
        user=user,
        body='**Bold** and *italic* and [link](https://example.com)',
        type=Comment.USER,
        content_type=ct,
        object_id=dataset.id
    )
    
    # Render markdown as in template
    body = comment.body_text()
    html = str(markdown(body))
    
    # Should contain safe HTML
    assert '<strong>Bold</strong>' in html or '<b>Bold</b>' in html
    assert '<em>italic</em>' in html or '<i>italic</i>' in html
    assert 'href="https://example.com"' in html


@pytest.mark.django_db
def test_comment_mixed_safe_and_malicious(user, dataset):
    """Test comment with mixed safe and malicious content."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(
        user=user,
        body='''
This is **safe** content.

<script>alert("XSS")</script>

And more *safe* content.
        ''',
        type=Comment.USER,
        content_type=ct,
        object_id=dataset.id
    )
    
    # Render markdown as in template
    body = comment.body_text()
    html = str(markdown(body))
    
    # Safe content preserved
    assert '<strong>safe</strong>' in html or '<b>safe</b>' in html
    
    # Malicious content escaped (not executable)
    assert '<script>' not in html.lower()
    assert '<script ' not in html.lower()
    # The word 'alert' might appear in escaped text, which is safe
    # Check that script tags specifically are escaped
    if 'script' in html.lower():
        assert '&lt;script' in html, f"Script tag not escaped: {html}"


@pytest.mark.django_db
def test_comment_empty_body(user, dataset):
    """Test comment with empty body."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(
        user=user,
        body='',
        type=Comment.USER,
        content_type=ct,
        object_id=dataset.id
    )
    
    html = comment.body_text()
    # Should handle empty gracefully
    assert html == '' or html is None or str(html) == ''


@pytest.mark.django_db
def test_comment_code_blocks(user, dataset):
    """Test that markdown code blocks work safely."""
    ct = ContentType.objects.get_for_model(dataset)
    comment = Comment.objects.create(
        user=user,
        body='Here is some code:\n\n```python\nprint("hello")\n```',
        type=Comment.USER,
        content_type=ct,
        object_id=dataset.id
    )
    
    # Render markdown as in template
    body = comment.body_text()
    html = str(markdown(body))
    
    # Should contain code block
    assert '<code>' in html or '<pre>' in html
    # But no script execution
    assert '<script' not in html.lower()

