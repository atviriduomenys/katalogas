from datetime import datetime
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, Client
from vitrina.compat.models import Redirections
from vitrina.datasets.factories import DatasetFactory
from django.test.utils import override_settings


class RedirectionsTest(TestCase):
    def setUp(self):
        self.c = Client()
        self.custom_dataset = DatasetFactory()
        self.ctype = ContentType.objects.get(model='dataset')
        Redirections.objects.create(created=datetime.now(),
                                    name="labas",
                                    path="/labas/",
                                    content_type=self.ctype,
                                    object_id=self.custom_dataset.pk)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['*'])
    def test_redirections_doesnt_exist(self):
        response = self.c.get('/neegzistuoja/')
        self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['*'])
    def test_redirections_exists(self):
        response = self.c.get('/labas/')
        self.assertEqual(response.status_code, 308)
