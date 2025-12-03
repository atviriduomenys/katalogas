from __future__ import annotations

import builtins
import csv
import io

import pytest
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from pprintpp import pprint as pp
from pytest_django.lazy_django import skip_if_no_django

from vitrina.datasets.models import DCATResourceSubclass

builtins.pp = pp


def _normalize_csv(csv_string: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(csv_string))
    rows = [row for row in reader if any(col.strip() for col in row)]
    return rows


@pytest.fixture(scope="session", autouse=True)
def manage_unmanaged_models():
    unmanaged_models = [m for m in apps.get_models() if not m._meta.managed]
    for model in unmanaged_models:
        model._meta.managed = True
    yield
    for model in unmanaged_models:
        model._meta.managed = False


@pytest.fixture()
def app(django_app_factory):
    yield django_app_factory(csrf_checks=False)


def pytest_configure(config):
    config.addinivalue_line("markers", "haystack: use a search index")


@pytest.fixture(autouse=True)
def _haystack_marker(request):
    if request.keywords.get("haystack"):
        # Skip if Django is not configured
        skip_if_no_django()

        # Haystack requires database
        request.getfixturevalue("db")

        # Switch to test index
        settings = request.getfixturevalue("settings")
        settings.HAYSTACK_CONNECTIONS = {
            "default": settings.HAYSTACK_CONNECTIONS["test"],
        }

        call_command("clear_index", interactive=False, using=["default"])


@pytest.fixture(scope="session", autouse=True)
def temp_media_root(tmp_path_factory):
    """Use a temporary directory for MEDIA_ROOT during tests."""
    from django.conf import settings

    media_dir = tmp_path_factory.mktemp("media")
    settings.MEDIA_ROOT = str(media_dir)

    internal_media_dir = tmp_path_factory.mktemp("internal-media")
    settings.INTERNAL_MEDIA_ROOT = str(internal_media_dir)
    return media_dir


@pytest.fixture(autouse=True)
def ensure_default_subclasses(db):
    obj, _ = DCATResourceSubclass.objects.get_or_create(name="dataset")
    if not obj.has_translation("lt"):
        obj.set_current_language("lt")
        obj.title = "Duomenų rinkinys"
        obj.save()

    obj2, _ = DCATResourceSubclass.objects.get_or_create(name="service")
    if not obj2.has_translation("lt"):
        obj2.set_current_language("lt")
        obj2.title = "Duomenų publikavimo paslauga"
        obj2.save()


# Common fixtures for security tests
@pytest.fixture
def user(db):
    """Create test user."""
    from vitrina.users.models import User

    return User.objects.create_user(
        email="test@example.com", first_name="Test", last_name="User", password="testpass123"
    )


@pytest.fixture
def organization(db):
    """Create test organization."""
    from vitrina.orgs.models import Organization

    return Organization.add_root(title="Test Organization", company_code="123456")


@pytest.fixture
def dataset(db, organization):
    """Create test dataset."""
    from vitrina.datasets.models import Dataset

    return Dataset.objects.create(title="Test Dataset", organization=organization)


@pytest.fixture(autouse=True)
def clear_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def mock_translation_service():
    TRANSLATION_MAPPING = {
        "Pavadinimas": "Title",
        "Aprašymas": "Description",
        "Būsena": "Status",
        "copyright": "autorių teisės",
        "license": "licencija",
        "restricted": "apribota",
    }

    class MockTranslationResponse:
        def __init__(self, text: str) -> None:
            self.status_code = 200
            self._text = text

        def json(self) -> str:
            return TRANSLATION_MAPPING.get(self._text, self._text)

        def raise_for_status(self) -> None:
            pass


@pytest.fixture(autouse=True, scope="session")
def disable_cms_toolbar():
    settings.CMS_TOOLBAR_ANONYMOUS_ON = False
    settings.CMS_TOOLBAR_ENABLED = False
