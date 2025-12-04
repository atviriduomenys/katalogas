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

        comment = RevisionComment(
            source=RevisionSource.VIEW,
            view=self._get_view_path(view_func),
            http_method=request.method,
            path=request.path,
            args=list(view_args),
            kwargs=view_kwargs,
        )
        reversion.set_comment(comment.to_json())
        return None
    
    def _get_view_path(self, view_func):
        # Class-based view
        view_class = getattr(view_func, "view_class", None)
        if view_class is not None:
            return f"{view_class.__module__}.{view_class.__name__}"

        # Function-based view (unwrap decorators)
        original = view_func
        while hasattr(original, "__wrapped__"):
            original = original.__wrapped__

        return f"{original.__module__}.{original.__name__}"
