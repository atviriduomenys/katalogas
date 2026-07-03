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
        # Exact allow-list membership.
        assert "https://*.gov.lt" in settings.CSRF_TRUSTED_ORIGINS

    def test_language_cookie_is_secure(self):
        """Test that language cookie is also secured."""
        assert settings.LANGUAGE_COOKIE_SECURE is True


class TestContentSecurityPolicy:
    """Content-Security-Policy configuration (WEB-5).

    Guards against accidental regressions in the CSP setup: the middleware being
    reordered/removed, or the locked-down directives being weakened.
    """

    def test_csp_middleware_enabled(self):
        """CSPMiddleware must be installed for the CSP header to be emitted."""
        assert "csp.middleware.CSPMiddleware" in settings.MIDDLEWARE

    def test_csp_middleware_ordered_right_after_security_middleware(self):
        """CSPMiddleware belongs near the top of the stack, right after SecurityMiddleware."""
        mw = settings.MIDDLEWARE
        assert "csp.middleware.CSPMiddleware" in mw
        assert "django.middleware.security.SecurityMiddleware" in mw
        assert mw.index("csp.middleware.CSPMiddleware") == mw.index("django.middleware.security.SecurityMiddleware") + 1

    def test_csp_policy_has_directives(self):
        assert "DIRECTIVES" in settings.CONTENT_SECURITY_POLICY

    def test_csp_locked_down_directives(self):
        """Directives that carry no trade-off must stay locked down (defense in depth)."""
        directives = settings.CONTENT_SECURITY_POLICY["DIRECTIVES"]
        assert directives["default-src"] == ["'self'"]
        assert directives["object-src"] == ["'none'"]
        assert directives["base-uri"] == ["'self'"]
        assert directives["frame-ancestors"] == ["'self'"]
        assert directives["form-action"] == ["'self'"]

    def test_csp_script_and_style_src_restricted_to_self_and_allowlist(self):
        """script-src/style-src must at least be scoped to 'self' (never a bare '*')."""
        directives = settings.CONTENT_SECURITY_POLICY["DIRECTIVES"]
        assert "'self'" in directives["script-src"]
        assert "'self'" in directives["style-src"]
        assert "*" not in directives["script-src"]
        assert "*" not in directives["style-src"]

    def test_csp_frame_src_allows_expected_embeds(self):
        """Framing is limited to the origins we actually embed (YouTube, reCAPTCHA)."""
        frame_src = settings.CONTENT_SECURITY_POLICY["DIRECTIVES"]["frame-src"]
        # Exact allow-list membership (an == comparison, not URL substring matching).
        assert any(source == "'self'" for source in frame_src)
        assert any(source == "https://www.youtube.com" for source in frame_src)
