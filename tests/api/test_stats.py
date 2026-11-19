import pytest
from django.urls import reverse
from django.utils import timezone
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory
from vitrina.projects.models import Project
from vitrina.search.models import DatasetSearchDoc
from vitrina.users.factories import UserFactory

COUNTERS = ("organizations", "datasets", "projects")


def _counts(app: DjangoTestApp, scope: str) -> dict[str, int]:
    res = app.get(reverse("api-stats"), {"scope": scope})
    assert res.json["scope"] == scope
    return {key: res.json[key] for key in COUNTERS}


def _create_stats_data():
    org = OrganizationFactory(is_public=True)
    hidden_org = OrganizationFactory(is_public=False)
    OrganizationFactory(is_public=True, deleted=True, deleted_on=timezone.now())

    DatasetFactory(organization=org)
    DatasetFactory(organization=org, is_public=False)
    DatasetFactory(organization=hidden_org, access_rights=Dataset.CONFIDENTIAL)
    DatasetFactory(organization=org, deleted=True, deleted_on=timezone.now())
    not_indexed = DatasetFactory(organization=org)
    DatasetSearchDoc.objects.filter(dataset=not_indexed).delete()

    ProjectFactory()
    ProjectFactory(is_public=False)
    ProjectFactory(status=Project.CREATED)
    ProjectFactory(deleted=True)
    ProjectFactory(deleted_on=timezone.now())


def _added(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    # Data migrations create some records, so only what the test adds is compared.
    return {key: after[key] - before[key] for key in COUNTERS}


@pytest.mark.django_db
def test_stats_default_scope_is_public(app: DjangoTestApp):
    assert app.get(reverse("api-stats")).json["scope"] == "public"


@pytest.mark.django_db
def test_stats_public_scope(app: DjangoTestApp):
    before = _counts(app, "public")
    _create_stats_data()
    assert _added(before, _counts(app, "public")) == {"organizations": 1, "datasets": 1, "projects": 1}


@pytest.mark.django_db
def test_stats_all_scope(app: DjangoTestApp):
    app.set_user(UserFactory())
    before = _counts(app, "all")
    _create_stats_data()
    assert _added(before, _counts(app, "all")) == {"organizations": 2, "datasets": 4, "projects": 2}


@pytest.mark.django_db
def test_stats_all_scope_requires_login(app: DjangoTestApp):
    res = app.get(reverse("api-stats"), {"scope": "all"}, expect_errors=True)
    assert res.status_code == 403
    assert res.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.django_db
def test_stats_public_ignores_requesting_user(app: DjangoTestApp):
    _create_stats_data()
    anonymous = _counts(app, "public")
    app.set_user(UserFactory(is_staff=True, is_superuser=True))
    assert _counts(app, "public") == anonymous


@pytest.mark.django_db
def test_stats_all_ignores_requesting_user(app: DjangoTestApp):
    _create_stats_data()
    app.set_user(UserFactory())
    regular = _counts(app, "all")
    app.set_user(UserFactory(is_staff=True, is_superuser=True))
    assert _counts(app, "all") == regular


@pytest.mark.django_db
def test_stats_public_scope_is_publicly_cached(app: DjangoTestApp, settings):
    # The hidden test toolbar disables caching on every response; production shows it.
    settings.CMS_TOOLBAR_HIDE = False
    res = app.get(reverse("api-stats"))
    assert res.headers["Access-Control-Allow-Origin"] == "*"
    assert res.headers["Cache-Control"] == "public, max-age=300"


@pytest.mark.django_db
def test_stats_all_scope_is_not_cached(app: DjangoTestApp):
    app.set_user(UserFactory())
    res = app.get(reverse("api-stats"), {"scope": "all"})
    assert "no-store" in res.headers["Cache-Control"]
    assert "public" not in res.headers["Cache-Control"]


@pytest.mark.django_db
def test_stats_invalid_scope(app: DjangoTestApp):
    res = app.get(reverse("api-stats"), {"scope": "secret"}, expect_errors=True)
    assert res.status_code == 400
    assert "Unsupported scope" in res.json["error"]
    assert res.headers["Access-Control-Allow-Origin"] == "*"
