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


@pytest.fixture
def stats_data():
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


@pytest.mark.django_db
def test_stats_default_scope_is_public(app: DjangoTestApp, stats_data):
    res = app.get(reverse("api-stats"))
    assert res.json == {"scope": "public", "organizations": 1, "datasets": 1, "projects": 1}


@pytest.mark.django_db
def test_stats_all_scope(app: DjangoTestApp, stats_data):
    app.set_user(UserFactory())
    res = app.get(reverse("api-stats"), {"scope": "all"})
    assert res.json == {"scope": "all", "organizations": 2, "datasets": 4, "projects": 2}


@pytest.mark.django_db
def test_stats_all_scope_requires_login(app: DjangoTestApp, stats_data):
    res = app.get(reverse("api-stats"), {"scope": "all"}, expect_errors=True)
    assert res.status_code == 403
    assert res.headers["Access-Control-Allow-Origin"] == "*"


@pytest.mark.django_db
def test_stats_public_ignores_requesting_user(app: DjangoTestApp, stats_data):
    anonymous = app.get(reverse("api-stats")).json
    app.set_user(UserFactory(is_staff=True, is_superuser=True))
    assert app.get(reverse("api-stats")).json == anonymous


@pytest.mark.django_db
def test_stats_all_ignores_requesting_user(app: DjangoTestApp, stats_data):
    app.set_user(UserFactory())
    regular = app.get(reverse("api-stats"), {"scope": "all"}).json
    app.set_user(UserFactory(is_staff=True, is_superuser=True))
    assert app.get(reverse("api-stats"), {"scope": "all"}).json == regular


@pytest.mark.django_db
def test_stats_headers(app: DjangoTestApp):
    res = app.get(reverse("api-stats"))
    assert res.headers["Access-Control-Allow-Origin"] == "*"
    assert res.headers["Cache-Control"] == "public, max-age=300"


@pytest.mark.django_db
def test_stats_all_scope_is_not_publicly_cached(app: DjangoTestApp):
    app.set_user(UserFactory())
    res = app.get(reverse("api-stats"), {"scope": "all"})
    assert res.headers["Cache-Control"] == "private, max-age=300"


@pytest.mark.django_db
def test_stats_invalid_scope(app: DjangoTestApp):
    res = app.get(reverse("api-stats"), {"scope": "secret"}, expect_errors=True)
    assert res.status_code == 400
    assert "Unsupported scope" in res.json["error"]
    assert res.headers["Access-Control-Allow-Origin"] == "*"
