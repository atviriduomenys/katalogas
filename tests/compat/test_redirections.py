import pytest
from django.test import Client
from django_webtest import DjangoTestApp
from django.contrib.redirects.models import Redirect


@pytest.mark.django_db
def test_redirection_doesnt_exist(app: DjangoTestApp):
    c = Client()
    response = c.get('/neegzistuoja/')
    assert response.status_code == 404


@pytest.mark.django_db
def test_redirection_exists_has_new_path(app: DjangoTestApp):
    c = Client()
    Redirect.objects.create(
        site_id=1,
        old_path='/labas/',
        new_path='/labas_naujas/',
    )
    response = c.get('/labas/')
    assert response.status_code == 301


@pytest.mark.django_db
def test_redirection_exists_no_new_path(app: DjangoTestApp):
    c = Client()
    Redirect.objects.create(
        site_id=1,
        old_path='/labas/',
    )
    response = c.get('/labas/')
    assert response.status_code == 410
