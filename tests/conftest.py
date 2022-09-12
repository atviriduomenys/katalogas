import pytest

from django.apps import apps


@pytest.fixture(scope='session', autouse=True)
def manage_unmanaged_models():
    unmanaged_models = [m for m in apps.get_models() if not m._meta.managed]
    for model in unmanaged_models:
        model._meta.managed = True
    yield
    for model in unmanaged_models:
        model._meta.managed = False


@pytest.fixture()
def app(django_app):
    yield django_app


@pytest.fixture
def csrf_exempt_django_app(django_app_factory):
    return django_app_factory(csrf_checks=False)
