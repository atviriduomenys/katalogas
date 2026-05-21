from datetime import timedelta
from typing import Any

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
