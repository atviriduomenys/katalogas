from datetime import timedelta

from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
import reversion
from vitrina.utils import RevisionComment, RevisionSource


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
    Automatically sets a default reversion comment based on the view
    and the view arguments, if a revision is active.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not reversion.is_active():
            return None

        if reversion.get_comment():
            return None

        if hasattr(view_func, "model_admin"):
            return None

        match = request.resolver_match

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
