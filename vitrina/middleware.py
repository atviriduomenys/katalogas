from django.utils.deprecation import MiddlewareMixin


class NoAutoLocaleMiddleware(MiddlewareMixin):

    def process_request(self, request):
        request.META['HTTP_ACCEPT_LANGUAGE'] = ''
