import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request


@pytest.mark.django_db
def test_request_create(csrf_exempt_django_app: DjangoTestApp):
    resp = csrf_exempt_django_app.post(reverse("request-create"), {
        'title': "Request",
        'description': "Description"
    })
    assert Request.objects.count() == 1
    assert resp.status_code == 302
    assert resp.url == reverse('request-detail', args=[Request.objects.first().pk])


@pytest.mark.django_db
def test_request_update(csrf_exempt_django_app: DjangoTestApp):
    request = RequestFactory()
    resp = csrf_exempt_django_app.post(reverse("request-update", args=[request.pk]), {
        'title': "Updated title",
        'description': "Updated description"
    })
    assert resp.status_code == 302
    assert resp.url == reverse('request-detail', args=[request.pk])
    assert Request.objects.first().title == "Updated title"
    assert Request.objects.first().description == "Updated description"
