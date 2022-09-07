import pytest
from django_webtest import DjangoTestApp
from django.contrib.redirects.models import Redirect


@pytest.mark.django_db
def test_redirection_doesnt_exist(app: DjangoTestApp):
    response = app.get('/neegzistuoja/', expect_errors=True)
    assert response.status_code == 404


@pytest.mark.django_db
def test_redirection_exists_has_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/labas/',
        new_path='/labas_naujas/',
    )
    response = app.get('/labas/')
    assert response.status_code == 301


@pytest.mark.django_db
def test_redirection_exists_no_new_path(app: DjangoTestApp):
    Redirect.objects.create(
        site_id=1,
        old_path='/labas/',
    )
    response = app.get('/labas/', expect_errors=True)
    assert response.status_code == 410
