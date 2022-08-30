from datetime import datetime

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, Client
from django_webtest import DjangoTestApp

from vitrina.compat.models import Redirections
from vitrina.datasets.factories import DatasetFactory
from django.test.utils import override_settings


@override_settings(DEBUG=False, ALLOWED_HOSTS=['*'])
@pytest.mark.django_db
def test_redirection_doesnt_exist(app: DjangoTestApp):
    c = Client()
    response = c.get('/neegzistuoja/')
    assert response.status_code == 404


@override_settings(DEBUG=False, ALLOWED_HOSTS=['*'])
@pytest.mark.django_db
def test_redirection_exists(app: DjangoTestApp):
    custom_dataset = DatasetFactory()
    ctype = ContentType.objects.get(model='dataset')
    Redirections.objects.create(created=datetime.now(),
                                name="labas",
                                path="/labas/",
                                content_type=ctype,
                                object_id=custom_dataset.pk)
    resp = app.get('/labas/')
    assert resp.status == '308 Permanent Redirect'
