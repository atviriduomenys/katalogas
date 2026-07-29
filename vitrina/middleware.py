from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
from django.http import HttpRequest
import reversion
from vitrina.log_context import reset_log_context, set_log_context
from vitrina.utils import RevisionComment, RevisionSource


class LogContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            token = set_log_context(user_id=user.pk)
            try:
                return self.get_response(request)
            finally:
                reset_log_context(token)
        return self.get_response(request)


class CSPScopeMiddleware:
    """Relax the Content-Security-Policy to the permissive (inline-allowing) policy for the
    Django admin, the coordinator admin and any request that renders the django-CMS toolbar
    (logged-in editors). Those surfaces emit third-party inline scripts/styles (admin widgets,
    CKEditor, the CMS toolbar) that cannot carry our nonce, so the strict nonce policy would
    break — or, in the current report-only phase, spam violation reports on them.

    Works with django-csp's per-response overrides, setting both the enforced (`_csp_replace`)
    and report-only (`_csp_replace_ro`) variants so it keeps working after the strict policy is
    promoted from report-only to enforced.

    MUST be listed AFTER ``csp.middleware.CSPMiddleware`` in MIDDLEWARE so that its response
    phase runs first and the override is in place before CSPMiddleware writes the header.
    """

    ADMIN_PREFIXES = ("/admin/", "/coordinator-admin/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if self._needs_permissive(request):
            override = {
                "script-src": settings.CSP_PERMISSIVE_SCRIPT_SRC,
                "style-src": settings.CSP_PERMISSIVE_STYLE_SRC,
            }
            response._csp_replace = override
            response._csp_replace_ro = override
        return response

    def _needs_permissive(self, request: HttpRequest) -> bool:
        if request.path_info.startswith(self.ADMIN_PREFIXES):
            return True
        toolbar = getattr(request, "toolbar", None)
        return bool(toolbar is not None and getattr(toolbar, "show_toolbar", False))


class NoAutoLocaleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.META["HTTP_ACCEPT_LANGUAGE"] = ""


class LogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user and request.user.is_authenticated:
            if not request.user.is_viisp_login and (
                request.user.password_last_updated is None
                or request.user.password_last_updated < (now() - timedelta(days=90))
            ):
                logout(request)
        response = self.get_response(request)
        return response


class NoCacheMiddleware:
    """Prevent browser from caching responses served to authenticated users.

    Must be placed after AuthenticationMiddleware so request.user is available.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(request, 'user', None) and request.user.is_authenticated:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
        return response


class AutoRevisionCommentMiddleware(MiddlewareMixin):
    """
    Automatically sets a default reversion comment for CUD operations based on the view
    and the view arguments, if a revision is active.
    """

    def process_view(
        self, request: HttpRequest, view_func: Any, view_args: list[Any], view_kwargs: dict[str, Any]
    ) -> None:
        if not reversion.is_active() or reversion.get_comment() or hasattr(view_func, "model_admin"):
            return None

        match = request.resolver_match

        if not match:
            return None

        comment = RevisionComment(
            source=RevisionSource.VIEW,
            action=match.url_name or match.view_name,
            http_method=request.method,
            path=request.path,
            args=list(view_args),
            kwargs=view_kwargs,
        )
        reversion.set_comment(comment.to_json())
        return None
