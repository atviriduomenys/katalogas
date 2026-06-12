import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory

ORG_COUNT = 55


@pytest.fixture
def many_orgs_with_datasets(db):
    for i in range(ORG_COUNT):
        DatasetFactory(organization=OrganizationFactory(title=f"Org {i:03d}"))


@pytest.mark.haystack
@pytest.mark.django_db
def test_sidebar_organization_filter_offers_all_organizations(app: DjangoTestApp, many_orgs_with_datasets):
    resp = app.get(reverse("dataset-list"))
    org_filter = next(f for f in resp.context["filters"] if f.name == "organization")
    assert len(list(org_filter.items())) == ORG_COUNT


@pytest.mark.haystack
@pytest.mark.django_db
def test_organization_stats_chart_includes_all_organizations(app: DjangoTestApp, many_orgs_with_datasets):
    resp = app.get(reverse("dataset-stats-organization"))
    assert len(resp.context["bar_chart_data"]) == ORG_COUNT
