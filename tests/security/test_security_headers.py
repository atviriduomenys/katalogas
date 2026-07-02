"""
Tests for security headers and cookie settings.
"""

from urllib.parse import urlsplit
from django.conf import settings
from django.test import Client


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
        # `any(origin == ...)` rather than the more natural `"..." in ...` only to avoid a
        # CodeQL incomplete-url-substring-sanitization false positive: list membership is
        # already an exact == match (CodeQL flags the `"<url>" in x` syntax regardless).
        assert any(origin == "https://*.gov.lt" for origin in settings.CSRF_TRUSTED_ORIGINS)

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

        # Smoke-test that the header is actually added to responses.
        response = Client(HTTP_HOST="localhost").get("/robots.txt")
        assert response.has_header("Content-Security-Policy")

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
        assert "'self'" in frame_src

        parsed_origins = set()
        for source in frame_src:
            if not isinstance(source, str):
                continue
            parsed = urlsplit(source)
            if parsed.scheme and parsed.hostname:
                origin = f"{parsed.scheme}://{parsed.hostname}"
                if parsed.port:
                    origin = f"{origin}:{parsed.port}"
                parsed_origins.add(origin)

        # Subset check on parsed origins (set operation, not URL substring matching).
        expected_embed_origins = {
            "https://www.youtube.com",
            "https://www.google.com",
            "https://www.gstatic.com",
        }
        assert expected_embed_origins <= parsed_origins


class TestStrictCspReportOnly:
    """Strict, nonce-based policy shipped as Content-Security-Policy-Report-Only (WEB-5).

    It runs alongside the still-permissive enforced policy so violations can be collected in a
    real environment before switching to enforcement.
    """

    def test_report_only_policy_defined(self):
        assert "DIRECTIVES" in settings.CONTENT_SECURITY_POLICY_REPORT_ONLY

    def test_enforced_policy_stays_permissive_while_reporting(self):
        """Nothing may actually be blocked while the strict policy is only being reported."""
        enforced = settings.CONTENT_SECURITY_POLICY["DIRECTIVES"]
        assert "'unsafe-inline'" in enforced["script-src"]
        assert "'unsafe-inline'" in enforced["style-src"]

    def test_report_only_uses_nonce_and_drops_unsafe_inline(self):
        from csp.constants import NONCE

        strict = settings.CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]
        assert NONCE in strict["script-src"]
        assert NONCE in strict["style-src"]
        assert "'unsafe-inline'" not in strict["script-src"]
        assert "'unsafe-inline'" not in strict["style-src"]

    def test_report_only_keeps_unsafe_eval_for_alpine(self):
        """Alpine.js (webpack/src/wizard.js) evaluates its directives with new Function()."""
        strict = settings.CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]
        assert "'unsafe-eval'" in strict["script-src"]

    def test_report_only_preserves_locked_down_directives(self):
        strict = settings.CONTENT_SECURITY_POLICY_REPORT_ONLY["DIRECTIVES"]
        assert strict["object-src"] == ["'none'"]
        assert strict["frame-ancestors"] == ["'self'"]


class TestCspScopeMiddleware:
    """CSPScopeMiddleware relaxes CSP to the permissive policy for admin / CMS surfaces (WEB-5)."""

    def test_middleware_enabled_right_after_csp_middleware(self):
        mw = settings.MIDDLEWARE
        assert "vitrina.middleware.CSPScopeMiddleware" in mw
        assert mw.index("vitrina.middleware.CSPScopeMiddleware") == mw.index("csp.middleware.CSPMiddleware") + 1

    @staticmethod
    def _report_only_script_src(path):
        """Drive the CSP + scope middleware pair for ``path`` and return its report-only script-src."""
        from django.test import RequestFactory
        from django.http import HttpResponse
        from csp.middleware import CSPMiddleware
        from vitrina.middleware import CSPScopeMiddleware

        def view(request):
            str(request.csp_nonce)  # emulate a template rendering {{ request.csp_nonce }}
            return HttpResponse("ok")

        # CSPMiddleware is the outer wrapper (listed first); CSPScopeMiddleware the inner one.
        stack = CSPMiddleware(get_response=CSPScopeMiddleware(get_response=view))
        response = stack(RequestFactory().get(path))
        header = response.headers.get("Content-Security-Policy-Report-Only", "")
        return next(p.strip() for p in header.split(";") if p.strip().startswith("script-src"))

    def test_public_page_reports_strict_nonce_policy(self):
        script_src = self._report_only_script_src("/")
        assert "'nonce-" in script_src
        assert "'unsafe-inline'" not in script_src

    def test_admin_page_relaxed_to_permissive(self):
        script_src = self._report_only_script_src("/admin/")
        assert "'unsafe-inline'" in script_src

    def test_coordinator_admin_relaxed_to_permissive(self):
        script_src = self._report_only_script_src("/coordinator-admin/foo/")
        assert "'unsafe-inline'" in script_src
