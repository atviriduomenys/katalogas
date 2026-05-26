import pytest
import pytz
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_webtest import DjangoTestApp
from freezegun import freeze_time

from datetime import date, datetime

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.statistics.factories import DatasetStatsFactory

from tests.stats_utils import FROZEN_NOW

INDICATORS = ["dataset-count", "object-count", "request-count"]

EXPECTED_YEAR = {
    "dataset-count": {
        "selected_year": "2022",
        "year_stats": {"2023-Q1": 1, "2022-Q3": 1, "2022-Q1": 1},
        "max_count": 1,
        "current_object": "year/2022",
        "active_filter": "publication",
        "active_indicator": "dataset-count",
        "sort": "sort-desc",
        "yAxis_title": "Duomenų rinkinių skaičius",
    },
    "object-count": {
        "selected_year": "2022",
        "year_stats": {"2023-Q1": 1, "2022-Q1": 40, "2022-Q3": 46},
        "max_count": 46,
        "current_object": "year/2022",
        "active_filter": "publication",
        "active_indicator": "object-count",
        "sort": "sort-desc",
        "yAxis_title": "Objektų skaičius",
    },
    "request-count": {
        "selected_year": "2022",
        "year_stats": {"2023-Q1": 1, "2022-Q1": 18, "2022-Q3": 21},
        "max_count": 21,
        "current_object": "year/2022",
        "active_filter": "publication",
        "active_indicator": "request-count",
        "sort": "sort-desc",
        "yAxis_title": "Poreikių skaičius",
    },
}

EXPECTED_QUARTER = {
    "dataset-count": {
        "selected_quarter": "2022-Q3",
        "year_stats": {"2022-09": 1},
        "max_count": 1,
        "current_object": "quarter/2022-Q3",
        "active_filter": "publication",
        "active_indicator": "dataset-count",
        "sort": "sort-desc",
        "yAxis_title": "Duomenų rinkinių skaičius",
    },
    "object-count": {
        "selected_quarter": "2022-Q3",
        "year_stats": {"2022-09": 46},
        "max_count": 46,
        "current_object": "quarter/2022-Q3",
        "active_filter": "publication",
        "active_indicator": "object-count",
        "sort": "sort-desc",
        "yAxis_title": "Objektų skaičius",
    },
    "request-count": {
        "selected_quarter": "2022-Q3",
        "year_stats": {"2022-09": 21},
        "max_count": 21,
        "current_object": "quarter/2022-Q3",
        "active_filter": "publication",
        "active_indicator": "request-count",
        "sort": "sort-desc",
        "yAxis_title": "Poreikių skaičius",
    },
}


@pytest.fixture()
def year_quarter_data(db):
    tz = pytz.timezone("Europe/Vilnius")

    org = OrganizationFactory()

    ds_a = DatasetFactory(
        organization=org,
        is_public=True,
        published=tz.localize(datetime(2022, 3, 15, 10, 0, 0)),
    )
    ds_b = DatasetFactory(
        organization=org,
        is_public=True,
        published=tz.localize(datetime(2023, 1, 10, 10, 0, 0)),
    )
    ds_c = DatasetFactory(
        organization=org,
        is_public=True,
        published=tz.localize(datetime(2022, 9, 5, 10, 0, 0)),
    )

    DatasetStatsFactory(dataset_id=ds_a.pk, created=date(2022, 3, 15), object_count=10, request_count=5)
    DatasetStatsFactory(dataset_id=ds_a.pk, created=date(2022, 6, 1), object_count=20, request_count=8)

    DatasetStatsFactory(dataset_id=ds_b.pk, created=date(2023, 1, 10), object_count=15, request_count=7)
    DatasetStatsFactory(dataset_id=ds_b.pk, created=date(2023, 3, 1), object_count=25, request_count=12)

    DatasetStatsFactory(dataset_id=ds_c.pk, created=date(2022, 9, 5), object_count=12, request_count=6)
    DatasetStatsFactory(dataset_id=ds_c.pk, created=date(2022, 11, 1), object_count=22, request_count=9)

    return [ds_a, ds_b, ds_c]


@pytest.mark.haystack
@pytest.mark.django_db
@pytest.mark.parametrize("indicator", INDICATORS)
def test_year_stats_snapshot(app: DjangoTestApp, year_quarter_data, indicator):
    with freeze_time(FROZEN_NOW):
        resp = app.get(
            reverse("dataset-stats-publication-year", kwargs={"year": 2022}),
            params={"indicator": indicator},
        )

    assert resp.status_code == 200

    snapshot = {
        "selected_year": resp.context["selected_year"],
        "year_stats": dict(resp.context["year_stats"]),
        "max_count": resp.context["max_count"],
        "current_object": resp.context["current_object"],
        "active_filter": resp.context["active_filter"],
        "active_indicator": resp.context["active_indicator"],
        "sort": resp.context["sort"],
        "yAxis_title": str(resp.context["yAxis_title"]),
    }

    expected = EXPECTED_YEAR[indicator]
    assert expected is not None, f"No snapshot for YearStatsView indicator={indicator!r}."
    assert snapshot["selected_year"] == expected["selected_year"], f"selected_year mismatch for {indicator!r}"
    assert snapshot["year_stats"] == expected["year_stats"], f"year_stats mismatch for {indicator!r}"
    assert snapshot["max_count"] == expected["max_count"], f"max_count mismatch for {indicator!r}"
    assert snapshot["current_object"] == expected["current_object"], f"current_object mismatch for {indicator!r}"
    assert snapshot["active_filter"] == expected["active_filter"], f"active_filter mismatch for {indicator!r}"
    assert snapshot["active_indicator"] == expected["active_indicator"], f"active_indicator mismatch for {indicator!r}"
    assert snapshot["sort"] == expected["sort"], f"sort mismatch for {indicator!r}"
    assert snapshot["yAxis_title"] == expected["yAxis_title"], f"yAxis_title mismatch for {indicator!r}"


@pytest.mark.haystack
@pytest.mark.django_db
@pytest.mark.parametrize("indicator", INDICATORS)
def test_quarter_stats_snapshot(app: DjangoTestApp, year_quarter_data, indicator):
    with freeze_time(FROZEN_NOW):
        resp = app.get(
            reverse("dataset-stats-publication-quarter", kwargs={"quarter": "2022-Q3"}),
            params={"indicator": indicator},
        )

    assert resp.status_code == 200

    snapshot = {
        "selected_quarter": resp.context["selected_quarter"],
        "year_stats": dict(resp.context["year_stats"]),
        "max_count": resp.context["max_count"],
        "current_object": resp.context["current_object"],
        "active_filter": resp.context["active_filter"],
        "active_indicator": resp.context["active_indicator"],
        "sort": resp.context["sort"],
        "yAxis_title": str(resp.context["yAxis_title"]),
    }

    expected = EXPECTED_QUARTER[indicator]
    assert expected is not None, f"No snapshot for QuarterStatsView indicator={indicator!r}."
    assert snapshot["selected_quarter"] == expected["selected_quarter"], f"selected_quarter mismatch for {indicator!r}"
    assert snapshot["year_stats"] == expected["year_stats"], f"year_stats mismatch for {indicator!r}"
    assert snapshot["max_count"] == expected["max_count"], f"max_count mismatch for {indicator!r}"
    assert snapshot["current_object"] == expected["current_object"], f"current_object mismatch for {indicator!r}"
    assert snapshot["active_filter"] == expected["active_filter"], f"active_filter mismatch for {indicator!r}"
    assert snapshot["active_indicator"] == expected["active_indicator"], f"active_indicator mismatch for {indicator!r}"
    assert snapshot["sort"] == expected["sort"], f"sort mismatch for {indicator!r}"
    assert snapshot["yAxis_title"] == expected["yAxis_title"], f"yAxis_title mismatch for {indicator!r}"


@pytest.mark.haystack
@pytest.mark.django_db
def test_year_stats_query_count(app: DjangoTestApp, year_quarter_data):
    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            app.get(
                reverse("dataset-stats-publication-year", kwargs={"year": 2022}),
                params={"indicator": "object-count"},
            )

    data_queries = [q for q in ctx.captured_queries if "dataset_statistic" in q["sql"]]
    assert len(data_queries) <= 5, (
        f"Expected ≤5 dataset_statistic queries but got {len(data_queries)}. "
        f"Pre-refactor baseline: 1 per quarter bucket."
    )


@pytest.mark.haystack
@pytest.mark.django_db
def test_quarter_stats_query_count(app: DjangoTestApp, year_quarter_data):
    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            app.get(
                reverse("dataset-stats-publication-quarter", kwargs={"quarter": "2022-Q3"}),
                params={"indicator": "object-count"},
            )

    data_queries = [q for q in ctx.captured_queries if "dataset_statistic" in q["sql"]]
    assert len(data_queries) <= 5, (
        f"Expected ≤5 dataset_statistic queries but got {len(data_queries)}. Pre-refactor baseline: 1 per month bucket."
    )
