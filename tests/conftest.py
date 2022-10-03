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


@pytest.fixture(autouse=True)
def _haystack_marker(request):
    """
    Implement the 'haystack' marker.

    This rebuilds the index at the start of each test and clears it at the end.

    Takes an optional connection parameter; if set, clears and rebuilds
    only the specified haystack connections.
    """
    marker = request.keywords.get('haystack', None)

    if marker:
        from pytest_django.lazy_django import skip_if_no_django
        from django.core.management import call_command
        request.getfixturevalue('db')

        # optional haystack connection parameter
        # if specified, pass to clear_index and rebuild_index
        connection = marker.kwargs.get('connection', None)
        index_args = {}
        if connection:
            index_args['using'] = connection

        def clear_index():
            call_command('clear_index', interactive=False, **index_args)

        # Skip if Django is not configured
        skip_if_no_django()

        request.addfinalizer(clear_index)

        call_command('rebuild_index', interactive=False, **index_args)
