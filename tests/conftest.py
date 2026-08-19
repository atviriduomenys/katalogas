from __future__ import annotations

import builtins
import csv
import io
from unittest.mock import patch

import pytest
from django.apps import apps
from pprintpp import pprint as pp

from vitrina.datasets.factories import DatasetFactory
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


@pytest.fixture(autouse=True)
def _immediate_search_indexing(request):
    """Index at once in tests that never commit.

    The search app defers indexing to the end of the transaction. A test that
    wraps itself in a rollback never commits, so the callback would never run.
    """
    django_db_marker = request.node.get_closest_marker("django_db")
    uses_real_transactions = django_db_marker and django_db_marker.kwargs.get("transaction", False)

    if uses_real_transactions:
        yield
    else:
        with patch("vitrina.search.signals.on_commit", lambda func: func()):
            yield


@pytest.fixture(scope="session", autouse=True)
def set_test_settings(tmp_path_factory):
    """Change django settings for tests"""
    from django.conf import settings

    # Change MEDIA_ROOT directories to temporary directories
    media_dir = tmp_path_factory.mktemp("media")
    settings.MEDIA_ROOT = str(media_dir)

    internal_media_dir = tmp_path_factory.mktemp("internal-media")
    settings.INTERNAL_MEDIA_ROOT = str(internal_media_dir)

    # Disable CMS toolbar in tests
    settings.CMS_TOOLBAR_HIDE = True


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
    dataset = DatasetFactory.create(title="Test Dataset", organization=organization)
    return dataset


@pytest.fixture(autouse=True)
def clear_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def mock_translate_text():
    TRANSLATION_MAPPING = {
        "Pavadinimas": "Title",
        "Aprašymas": "Description",
        "Būsena": "Status",
    }

    def fake_translate(text, field_name=""):
        return TRANSLATION_MAPPING.get(text, text)

    patches = [
        patch("vitrina.utils.translate_text", side_effect=fake_translate),
        patch("vitrina.resources.models.translate_text", side_effect=fake_translate),
    ]

    for _patch in patches:
        _patch.start()
    yield
    for _patch in patches:
        _patch.stop()


@pytest.fixture(autouse=True)
def enable_publish_button_flag(settings):
    """Enable publish_button flag for all tests"""
    settings.FLAGS = {
        "publish_button": [
            {"condition": "boolean", "value": True},
        ],
    }
