from datetime import timedelta

from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now


class NoAutoLocaleMiddleware(MiddlewareMixin):

    def process_request(self, request):
        request.META['HTTP_ACCEPT_LANGUAGE'] = ''


class LogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user and request.user.is_authenticated:
            if (
                not request.user.is_viisp_login and (
                    request.user.password_last_updated is None or
                    request.user.password_last_updated < (now() - timedelta(days=90))
                )
            ):
                logout(request)
        response = self.get_response(request)
        return response
