from django.urls import reverse
from django_webtest import WebTest

from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request


class RequestCreateTest(WebTest):
    csrf_checks = False

    def test_request_create(self):
        resp = self.app.post(reverse("request-create"), {'title': "Request", 'description': "Description"})
        self.assertEqual(Request.objects.count(), 1)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('request-detail', args=[Request.objects.first().pk]))


class RequestUpdateTest(WebTest):
    csrf_checks = False

    def setUp(self):
        self.request = RequestFactory()

    def test_request_update(self):
        resp = self.app.post(reverse("request-update", args=[self.request.pk]), {
            'title': "Updated title",
            'description': "Updated description"
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('request-detail', args=[self.request.pk]))
        self.assertEqual(Request.objects.first().title, "Updated title")
        self.assertEqual(Request.objects.first().description, "Updated description")
