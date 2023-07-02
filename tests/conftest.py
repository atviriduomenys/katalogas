import builtins

import pytest

from django.apps import apps
from django.core.management import call_command

from pytest_django.lazy_django import skip_if_no_django

from pprintpp import pprint as pp


builtins.pp = pp


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


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "haystack: use a search index"
    )


@pytest.fixture(autouse=True)
def _haystack_marker(request):
    if request.keywords.get('haystack'):
        # Skip if Django is not configured
        skip_if_no_django()

        # Haystack requires database
        request.getfixturevalue('db')

        # Switch to test index
        settings = request.getfixturevalue('settings')
        settings.HAYSTACK_CONNECTIONS = {
            'default': settings.HAYSTACK_CONNECTIONS['test'],
        }

        call_command('clear_index', interactive=False, using=['default'])
