"""
Tests for security headers and cookie settings.
"""

from django.conf import settings


class TestSecuritySettings:
    """Test security-related Django settings."""

    def test_hsts_configuration(self):
        """Test HSTS (HTTP Strict Transport Security) settings (WEB-9)."""
        # Should be 2 years (63072000 seconds) for preload list
        assert settings.SECURE_HSTS_SECONDS == 63072000

        # Should include subdomains
        assert settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True

        # Should be ready for preload
        assert settings.SECURE_HSTS_PRELOAD is True

    def test_referrer_policy(self):
        """Test Referrer-Policy header configuration."""
        # Prevents leaking full URLs to external sites
        assert settings.SECURE_REFERRER_POLICY == "strict-origin-when-cross-origin"

    def test_cookie_security_flags(self):
        """Test session and CSRF cookie security flags (WEB-6)."""
        # Secure flag (HTTPS only)
        assert settings.SESSION_COOKIE_SECURE is True
        assert settings.CSRF_COOKIE_SECURE is True

        # SameSite flag (CSRF protection)
        assert settings.SESSION_COOKIE_SAMESITE == "Lax"
        assert settings.CSRF_COOKIE_SAMESITE == "Lax"

        # HttpOnly flag (XSS protection)
        assert settings.SESSION_COOKIE_HTTPONLY is True
        # Note: CSRF_COOKIE_HTTPONLY is NOT set because jquery.postcsrf.js
        # needs to read the CSRF cookie for hitcount tracking


class TestProductionSecurityHeaders:
    """
    Test security headers configuration for production environments.

    Note: These tests verify settings, not actual HTTP responses.
    In production with HTTPS, Django will automatically apply these
    security attributes to cookies and headers.
    """

    def test_hsts_will_be_enforced_in_production(self):
        """Verify HSTS settings are configured for production enforcement."""
        # With these settings, Django's SecurityMiddleware will add
        # the HSTS header in production (when served over HTTPS)
        assert settings.SECURE_HSTS_SECONDS == 63072000
        assert settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
        assert settings.SECURE_HSTS_PRELOAD is True

        # Expected header in production:
        # Strict-Transport-Security: max-age=63072000; includeSubDomains; preload

    def test_cookie_security_will_be_enforced_in_production(self):
        """Verify cookie security settings are configured for production enforcement."""
        # With these settings, Django will automatically set cookie attributes
        # in production (when served over HTTPS)

        # Session cookies will have: Secure; HttpOnly; SameSite=Lax
        assert settings.SESSION_COOKIE_SECURE is True
        assert settings.SESSION_COOKIE_SAMESITE == "Lax"
        assert settings.SESSION_COOKIE_HTTPONLY is True

        # CSRF cookies will have: Secure; SameSite=Lax
        # Note: CSRF_COOKIE_HTTPONLY is deliberately NOT set because
        # jquery.postcsrf.js needs JavaScript access to read the token
        assert settings.CSRF_COOKIE_SECURE is True
        assert settings.CSRF_COOKIE_SAMESITE == "Lax"


class TestSecureDefaults:
    """Test that security defaults are properly set."""

    def test_csrf_trusted_origins_configured(self):
        """Test that CSRF trusted origins are configured."""
        assert "https://*.gov.lt" in settings.CSRF_TRUSTED_ORIGINS

    def test_language_cookie_is_secure(self):
        """Test that language cookie is also secured."""
        assert settings.LANGUAGE_COOKIE_SECURE is True
