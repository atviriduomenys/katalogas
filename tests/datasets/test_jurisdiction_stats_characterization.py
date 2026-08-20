import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun import freeze_time

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.views import JurisdictionStatsView
from vitrina.orgs.factories import OrganizationFactory
from vitrina.statistics.factories import DatasetStatsFactory

from tests.stats_utils import FROZEN_NOW, get_stats_context

INDICATORS = ["dataset-count", "object-count", "request-count"]

EXPECTED = {
    "dataset-count": {
        "single_org": True,
        "max_count": 1,
        "active_filter": "jurisdiction",
        "active_indicator": "dataset-count",
        "sort": "sort-desc",
        "jurisdiction_data_counts": [1, 1, 0],
        "jurisdiction_data_has_orgs": [False, False, False],
    },
    "object-count": {
        "single_org": True,
        "max_count": 30,
        "active_filter": "jurisdiction",
        "active_indicator": "object-count",
        "sort": "sort-desc",
        "jurisdiction_data_counts": [30, 15, 0],
        "jurisdiction_data_has_orgs": [False, False, False],
    },
    "request-count": {
        "single_org": True,
        "max_count": 13,
        "active_filter": "jurisdiction",
        "active_indicator": "request-count",
        "sort": "sort-desc",
        "jurisdiction_data_counts": [13, 7, 0],
        "jurisdiction_data_has_orgs": [False, False, False],
    },
}


@pytest.fixture
def jurisdiction_data(db):
    parent_org = type(OrganizationFactory.build()).add_root(
        title="Parent Org Jurisdiction",
        name="datasets/gov/test/jur/parent/",
        company_code="JURPAR0001",
        email="jurparent@test.lt",
        phone="+37060100000",
        address="Parent St 1",
        is_public=True,
        version=1,
    )

    child_a = parent_org.add_child(
        title="Child Org A",
        name="datasets/gov/test/jur/child_a/",
        company_code="JURCHILDA1",
        email="child_a@test.lt",
        phone="+37060100001",
        address="Child A St 1",
        is_public=True,
        version=1,
    )
    child_b = parent_org.add_child(
        title="Child Org B",
        name="datasets/gov/test/jur/child_b/",
        company_code="JURCHILDB1",
        email="child_b@test.lt",
        phone="+37060100002",
        address="Child B St 1",
        is_public=True,
        version=1,
    )
    child_c = parent_org.add_child(
        title="Child Org C",
        name="datasets/gov/test/jur/child_c/",
        company_code="JURCHILDC1",
        email="child_c@test.lt",
        phone="+37060100003",
        address="Child C St 1",
        is_public=True,
        version=1,
    )

    ds_a = DatasetFactory(organization=child_a, is_public=True)
    ds_b = DatasetFactory(organization=child_b, is_public=True)

    DatasetStatsFactory(dataset_id=ds_a.pk, object_count=10, request_count=5)
    DatasetStatsFactory(dataset_id=ds_a.pk, object_count=20, request_count=8)
    DatasetStatsFactory(dataset_id=ds_b.pk, object_count=15, request_count=7)

    return parent_org, child_a, child_b, child_c


@pytest.mark.django_db
@pytest.mark.parametrize("indicator", INDICATORS)
def test_jurisdiction_stats_snapshot(jurisdiction_data, indicator):
    parent_org, child_a, child_b, child_c = jurisdiction_data

    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            JurisdictionStatsView,
            reverse("dataset-stats-jurisdiction-children", kwargs={"pk": parent_org.pk}),
            params={"indicator": indicator, "sort": "sort-desc"},
            pk=parent_org.pk,
        )
    assert ctx is not None

    expected = EXPECTED[indicator]

    jdata = ctx["jurisdiction_data"]

    assert any(d["count"] > 0 for d in jdata), (
        f"All counts are zero for indicator={indicator}; fixture may not be seeded correctly"
    )
    assert len(jdata) == 3, f"Expected 3 child orgs but got {len(jdata)}"

    assert ctx["single_org"] == expected["single_org"]
    assert ctx["max_count"] == expected["max_count"]
    assert ctx["current_object"] == parent_org.pk
    assert ctx["active_filter"] == expected["active_filter"]
    assert ctx["active_indicator"] == expected["active_indicator"]
    assert ctx["sort"] == expected["sort"]

    assert [d["count"] for d in jdata] == expected["jurisdiction_data_counts"], (
        f"Counts mismatch for indicator={indicator}: got {[d['count'] for d in jdata]}"
    )
    assert [d["has_orgs"] for d in jdata] == expected["jurisdiction_data_has_orgs"]

    for d in jdata:
        assert "id" in d
        assert "title" in d
        assert "url" in d
        assert "has_orgs" in d
        assert "count" in d


@pytest.mark.django_db
def test_jurisdiction_stats_query_count(jurisdiction_data):
    parent_org, *_ = jurisdiction_data

    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            get_stats_context(
                JurisdictionStatsView,
                reverse("dataset-stats-jurisdiction-children", kwargs={"pk": parent_org.pk}),
                params={"indicator": "object-count", "sort": "sort-desc"},
                pk=parent_org.pk,
            )

    stats_queries = [
        q for q in ctx.captured_queries if "dataset_statistic" in q["sql"] and "SELECT" in q["sql"].upper()
    ]
    assert len(stats_queries) <= 1, (
        f"Expected ≤1 dataset_statistic SELECT queries but got {len(stats_queries)}. "
        f"The N+1 pattern may have been reintroduced (pre-refactor baseline: 2)."
    )
