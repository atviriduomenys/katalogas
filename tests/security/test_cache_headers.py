from unittest.mock import Mock

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

from vitrina.middleware import NoCacheMiddleware


ALL_PATHS = [
    "/datasets/",
    "/projects/",
    "/requests/",
    "/update-request-jurisdiction-filters/",
    "/update-request-org-filters/",
    "/partner/api/",
    "/partner/api/1/datasets",
    "/opening-tips/",
    "/opening-tips/saugykla/",
    "/robots.txt",
    "/",
    "/static/css/style.css",
]


def _apply_middleware(path, *, authenticated):
    def view(request):
        return HttpResponse("ok")

    request = RequestFactory().get(path)
    request.user = Mock(is_authenticated=True) if authenticated else AnonymousUser()
    return NoCacheMiddleware(get_response=view)(request)


@pytest.mark.parametrize("path", ALL_PATHS)
def test_authenticated_user_gets_no_cache_headers(path):
    response = _apply_middleware(path, authenticated=True)
    assert "no-cache" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]
    assert response["Pragma"] == "no-cache"


@pytest.mark.parametrize("path", ALL_PATHS)
def test_anonymous_user_does_not_get_no_cache_headers(path):
    response = _apply_middleware(path, authenticated=False)
    assert "Cache-Control" not in response
    assert "Pragma" not in response
