from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun import freeze_time

from vitrina.datasets.factories import DatasetFactory
from vitrina.plans.factories import PlanFactory
from vitrina.plans.models import PlanRequest
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request
from vitrina.requests.views import RequestPublicationStatsView, RequestQuarterStatsView, RequestYearStatsView

from tests.stats_utils import FROZEN_NOW, get_stats_context

PUB_INDICATORS = ["request-count", "request-count-open", "request-count-late"]
PUB_DURATIONS = [
    "duration-yearly",
    "duration-quarterly",
    "duration-monthly",
]


@pytest.fixture()
def request_pub_data(db):
    ds = DatasetFactory()

    def make_request(status):
        return RequestFactory(status=status, dataset=ds)

    with freeze_time("2022-12-28 10:00:00"):
        req_2022_a = make_request(Request.CREATED)
        make_request(Request.CREATED)
        make_request(Request.CREATED)

    with freeze_time("2023-01-03 10:00:00"):
        make_request(Request.CREATED)
        make_request(Request.CREATED)

    with freeze_time("2022-12-28 10:00:00"):
        make_request(Request.REJECTED)
        make_request(Request.REJECTED)

    with freeze_time("2023-01-03 10:00:00"):
        make_request(Request.REJECTED)

    plan = PlanFactory(deadline=date(2022, 1, 1))
    PlanRequest.objects.create(plan=plan, request=req_2022_a)

    return None


EXPECTED_PUB = {
    ("request-count", "duration-yearly"): {
        "year_stats": {"2022": 5, "2023": 3},
        "max_count": 5,
        "active_filter": "created",
        "active_indicator": "request-count",
        "sort": "sort-desc",
        "bar_chart_data_counts": [5, 3],
    },
    ("request-count", "duration-quarterly"): {
        "year_stats": {"2022": 5, "2023": 3},
        "max_count": 5,
        "active_filter": "created",
        "active_indicator": "request-count",
        "sort": "sort-desc",
        "bar_chart_data_counts": [5, 3, 0],
    },
    ("request-count", "duration-monthly"): {
        "year_stats": {"2022": 5, "2023": 3},
        "max_count": 5,
        "active_filter": "created",
        "active_indicator": "request-count",
        "sort": "sort-desc",
        "bar_chart_data_counts": [5, 3, 0, 0, 0, 0, 0],
    },
    ("request-count-open", "duration-yearly"): {
        "year_stats": {"2022": 3, "2023": 2},
        "max_count": 3,
        "active_filter": "created",
        "active_indicator": "request-count-open",
        "sort": "sort-desc",
        "bar_chart_data_counts": [3, 2],
    },
    ("request-count-open", "duration-quarterly"): {
        "year_stats": {"2022": 3, "2023": 2},
        "max_count": 3,
        "active_filter": "created",
        "active_indicator": "request-count-open",
        "sort": "sort-desc",
        "bar_chart_data_counts": [0, 0, 0],
    },
    ("request-count-open", "duration-monthly"): {
        "year_stats": {"2022": 3, "2023": 2},
        "max_count": 3,
        "active_filter": "created",
        "active_indicator": "request-count-open",
        "sort": "sort-desc",
        "bar_chart_data_counts": [0, 0, 0, 0, 0, 0, 0],
    },
    ("request-count-late", "duration-yearly"): {
        "year_stats": {"2022": 1, "2023": 0},
        "max_count": 1,
        "active_filter": "created",
        "active_indicator": "request-count-late",
        "sort": "sort-desc",
        "bar_chart_data_counts": [1, 0],
    },
    ("request-count-late", "duration-quarterly"): {
        "year_stats": {"2022": 1, "2023": 0},
        "max_count": 1,
        "active_filter": "created",
        "active_indicator": "request-count-late",
        "sort": "sort-desc",
        "bar_chart_data_counts": [0, 0, 0],
    },
    ("request-count-late", "duration-monthly"): {
        "year_stats": {"2022": 1, "2023": 0},
        "max_count": 1,
        "active_filter": "created",
        "active_indicator": "request-count-late",
        "sort": "sort-desc",
        "bar_chart_data_counts": [0, 0, 0, 0, 0, 0, 0],
    },
}


@pytest.mark.django_db
@pytest.mark.parametrize("indicator", PUB_INDICATORS)
@pytest.mark.parametrize("duration", PUB_DURATIONS)
def test_request_publication_stats_snapshot(request_pub_data, indicator, duration):
    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            RequestPublicationStatsView,
            reverse("request-stats-created"),
            params={"indicator": indicator, "duration": duration},
        )
    assert ctx is not None

    snapshot = {
        "year_stats": dict(ctx["year_stats"]),
        "max_count": ctx["max_count"],
        "active_filter": ctx["active_filter"],
        "active_indicator": ctx["active_indicator"],
        "sort": ctx["sort"],
        "bar_chart_data_counts": sorted([item["count"] for item in ctx["bar_chart_data"]], reverse=True),
    }

    key = (indicator, duration)
    assert key in EXPECTED_PUB, f"No snapshot for {key}."
    expected = EXPECTED_PUB[key]

    assert snapshot["year_stats"] == expected["year_stats"], (
        f"year_stats mismatch for {key}: got {snapshot['year_stats']!r}, expected {expected['year_stats']!r}"
    )
    assert snapshot["max_count"] == expected["max_count"], f"max_count mismatch for {key}"
    assert snapshot["active_filter"] == expected["active_filter"], f"active_filter mismatch for {key}"
    assert snapshot["active_indicator"] == expected["active_indicator"], f"active_indicator mismatch for {key}"
    assert snapshot["sort"] == expected["sort"], f"sort mismatch for {key}"
    assert snapshot["bar_chart_data_counts"] == expected["bar_chart_data_counts"], (
        f"bar_chart_data_counts mismatch for {key}: got {snapshot['bar_chart_data_counts']!r}"
    )


@pytest.mark.django_db
def test_request_publication_stats_query_count_open(request_pub_data):
    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            get_stats_context(
                RequestPublicationStatsView,
                reverse("request-stats-created"),
                params={"indicator": "request-count-open", "duration": "duration-yearly"},
            )

    request_queries = [q for q in ctx.captured_queries if '"vitrina_requests_request"' in q["sql"]]
    assert len(request_queries) <= 10, (
        f"Expected ≤10 request-table queries but got {len(request_queries)}. "
        f"N+1 pattern may be present (pre-refactor: 1 query/year)."
    )


@pytest.mark.django_db
def test_request_publication_stats_query_count_late(request_pub_data):
    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            get_stats_context(
                RequestPublicationStatsView,
                reverse("request-stats-created"),
                params={"indicator": "request-count-late", "duration": "duration-yearly"},
            )

    plan_request_queries = [q for q in ctx.captured_queries if '"plan_request"' in q["sql"]]
    assert len(plan_request_queries) <= 5, (
        f"Expected ≤5 plan_request queries but got {len(plan_request_queries)}. "
        f"N+1 pattern may be present (pre-refactor: 1 query/year)."
    )


@pytest.fixture()
def request_late_multiplan_data(db):
    ds = DatasetFactory()

    with freeze_time("2022-12-28 10:00:00"):
        req = RequestFactory(status=Request.CREATED, dataset=ds)

    plan_a = PlanFactory(deadline=date(2022, 1, 1))
    plan_b = PlanFactory(deadline=date(2022, 6, 1))
    PlanRequest.objects.create(plan=plan_a, request=req)
    PlanRequest.objects.create(plan=plan_b, request=req)

    return req


@pytest.mark.django_db
def test_request_count_late_counts_plan_request_rows(request_late_multiplan_data):
    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            RequestPublicationStatsView,
            reverse("request-stats-created"),
            params={"indicator": "request-count-late", "duration": "duration-yearly"},
        )
    assert ctx is not None

    year_stats = dict(ctx["year_stats"])
    assert year_stats == {"2022": 2}, (
        f"Expected request-count-late year_stats {{'2022': 2}} (PlanRequest ROW count), "
        f"got {year_stats!r}. A request in 2 past-deadline plans must count as 2, not 1."
    )
    assert ctx["max_count"] == 2, f"Expected max_count=2, got {ctx['max_count']!r}"


EXPECTED_YEAR = {
    None: {
        "selected_year": "2022",
        "year_stats_keys_subset": ["2022-Q4"],  # at minimum Q4 present
        "max_count_ge": 3,  # at least 3 (5 in Q4)
        "current_object": "year/2022",
        "filter": "publication",
        "sort": None,
    },
}


@pytest.mark.django_db
def test_request_year_stats_snapshot(request_pub_data):
    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            RequestYearStatsView,
            reverse("request-stats-publication-year", kwargs={"year": 2022}),
            year=2022,
        )
    assert ctx is not None

    year_stats = dict(ctx["year_stats"])
    max_count = ctx["max_count"]
    current_object = ctx["current_object"]
    filter_val = ctx["filter"]
    selected_year = ctx["selected_year"]
    ctx["sort"]

    expected_year_stats = {"2022-Q4": 5, "2023-Q1": 3}
    assert year_stats == expected_year_stats, (
        f"year_stats mismatch: got {year_stats!r}, expected {expected_year_stats!r}"
    )
    assert max_count == 5, f"max_count mismatch: got {max_count!r}, expected 5"
    assert current_object == "year/2022"
    assert filter_val == "publication"
    assert selected_year == "2022"


@pytest.mark.django_db
def test_request_quarter_stats_snapshot(request_pub_data):
    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            RequestQuarterStatsView,
            reverse("request-stats-publication-quarter", kwargs={"quarter": "2022-Q4"}),
            quarter="2022-Q4",
        )
    assert ctx is not None

    year_stats = dict(ctx["year_stats"])
    max_count = ctx["max_count"]
    current_object = ctx["current_object"]
    filter_val = ctx["filter"]
    selected_quarter = ctx["selected_quarter"]
    ctx["sort"]

    expected_quarter_stats = {"2022-12": 5}
    assert year_stats == expected_quarter_stats, (
        f"year_stats mismatch: got {year_stats!r}, expected {expected_quarter_stats!r}"
    )
    assert max_count == 5, f"max_count mismatch: got {max_count!r}, expected 5"
    assert current_object == "quarter/2022-Q4"
    assert filter_val == "publication"
    assert selected_quarter == "2022-Q4"
