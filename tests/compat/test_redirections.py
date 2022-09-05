from django_webtest import WebTest
from django.contrib.redirects.models import Redirect


class RedirectionsTest(WebTest):
    def test_redirection_doesnt_exist(self):
        response = self.client.get('/neegzistuoja/')
        self.assertEqual(response.status_code, 404)

    def test_redirection_exists_has_new_path(self):
        Redirect.objects.create(
            site_id=1,
            old_path='/labas/',
            new_path='/labas_naujas/',
        )
        response = self.client.get('/labas/')
        self.assertEqual(response.status_code, 301)

    def test_redirection_exists_no_new_path(self):
        Redirect.objects.create(
            site_id=1,
            old_path='/labas/',
        )
        response = self.client.get('/labas/')
        self.assertEqual(response.status_code, 410)
