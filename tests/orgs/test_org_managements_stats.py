import json

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from vitrina.classifiers.models import AreaOfManagement
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.views import OrganizationManagementsView

from tests.stats_utils import DURATIONS, FROZEN_NOW, get_stats_context

JUR1_LABEL = "Lietuvos Respublikos ekonomikos ir inovacijų ministerija"
JUR2_LABEL = "Lietuvos Respublikos energetikos ministerija"

EXPECTED = {
    "duration-yearly": {
        "time_chart_data": (
            '[{"label": "' + JUR1_LABEL + '", "data": ['
            '{"x": "2019", "y": 0}, {"x": "2020", "y": 0}, {"x": "2021", "y": 0}, '
            '{"x": "2022", "y": 1}, {"x": "2023", "y": 1}], "borderWidth": 1, "fill": true}, '
            '{"label": "' + JUR2_LABEL + '", "data": ['
            '{"x": "2019", "y": 0}, {"x": "2020", "y": 0}, {"x": "2021", "y": 0}, '
            '{"x": "2022", "y": 0}, {"x": "2023", "y": 1}], "borderWidth": 1, "fill": true}]'
        ),
        "bar_chart_data_titles_counts": [
            (JUR1_LABEL, 2),
            (JUR2_LABEL, 1),
        ],
        "max_count": 2,
    },
    "duration-quarterly": {
        "time_chart_data": (
            '[{"label": "' + JUR1_LABEL + '", "data": ['
            '{"x": "2021 Bir", "y": 0}, {"x": "2021 Rugs", "y": 0}, {"x": "2021 Grd", "y": 0}, '
            '{"x": "2022 Kov", "y": 0}, {"x": "2022 Bir", "y": 0}, {"x": "2022 Rugs", "y": 0}, '
            '{"x": "2022 Grd", "y": 1}, {"x": "2023 Kov", "y": 0}, {"x": "2023 Bir", "y": 1}], '
            '"borderWidth": 1, "fill": true}, '
            '{"label": "' + JUR2_LABEL + '", "data": ['
            '{"x": "2021 Bir", "y": 0}, {"x": "2021 Rugs", "y": 0}, {"x": "2021 Grd", "y": 0}, '
            '{"x": "2022 Kov", "y": 0}, {"x": "2022 Bir", "y": 0}, {"x": "2022 Rugs", "y": 0}, '
            '{"x": "2022 Grd", "y": 0}, {"x": "2023 Kov", "y": 1}, {"x": "2023 Bir", "y": 0}], '
            '"borderWidth": 1, "fill": true}]'
        ),
        "bar_chart_data_titles_counts": [
            (JUR1_LABEL, 2),
            (JUR2_LABEL, 1),
        ],
        "max_count": 2,
    },
    "duration-monthly": {
        "time_chart_data": (
            '[{"label": "' + JUR1_LABEL + '", "data": ['
            '{"x": "2022 06", "y": 0}, {"x": "2022 07", "y": 0}, {"x": "2022 08", "y": 0}, '
            '{"x": "2022 09", "y": 0}, {"x": "2022 10", "y": 0}, {"x": "2022 11", "y": 0}, '
            '{"x": "2022 12", "y": 1}, {"x": "2023 01", "y": 0}, {"x": "2023 02", "y": 0}, '
            '{"x": "2023 03", "y": 0}, {"x": "2023 04", "y": 0}, {"x": "2023 05", "y": 0}, '
            '{"x": "2023 06", "y": 1}], "borderWidth": 1, "fill": true}, '
            '{"label": "' + JUR2_LABEL + '", "data": ['
            '{"x": "2022 06", "y": 0}, {"x": "2022 07", "y": 0}, {"x": "2022 08", "y": 0}, '
            '{"x": "2022 09", "y": 0}, {"x": "2022 10", "y": 0}, {"x": "2022 11", "y": 0}, '
            '{"x": "2022 12", "y": 0}, {"x": "2023 01", "y": 0}, {"x": "2023 02", "y": 0}, '
            '{"x": "2023 03", "y": 1}, {"x": "2023 04", "y": 0}, {"x": "2023 05", "y": 0}, '
            '{"x": "2023 06", "y": 0}], "borderWidth": 1, "fill": true}]'
        ),
        "bar_chart_data_titles_counts": [
            (JUR1_LABEL, 2),
            (JUR2_LABEL, 1),
        ],
        "max_count": 2,
    },
    "duration-weekly": {
        "time_chart_data": (
            '[{"label": "' + JUR1_LABEL + '", "data": ['
            '{"x": "2022 50", "y": 0}, {"x": "2022 51", "y": 0}, {"x": "2022 52", "y": 0}, '
            '{"x": "2023 1", "y": 0}, {"x": "2023 2", "y": 0}, {"x": "2023 3", "y": 0}, '
            '{"x": "2023 4", "y": 0}, {"x": "2023 5", "y": 0}, {"x": "2023 6", "y": 0}, '
            '{"x": "2023 7", "y": 0}, {"x": "2023 8", "y": 0}, {"x": "2023 9", "y": 0}, '
            '{"x": "2023 10", "y": 0}, {"x": "2023 11", "y": 0}, {"x": "2023 12", "y": 0}, '
            '{"x": "2023 13", "y": 0}, {"x": "2023 14", "y": 0}, {"x": "2023 15", "y": 0}, '
            '{"x": "2023 16", "y": 0}, {"x": "2023 17", "y": 0}, {"x": "2023 18", "y": 0}, '
            '{"x": "2023 19", "y": 0}, {"x": "2023 20", "y": 0}, {"x": "2023 21", "y": 0}, '
            '{"x": "2023 22", "y": 0}, {"x": "2023 23", "y": 1}, {"x": "2023 24", "y": 0}], '
            '"borderWidth": 1, "fill": true}, '
            '{"label": "' + JUR2_LABEL + '", "data": ['
            '{"x": "2022 50", "y": 0}, {"x": "2022 51", "y": 0}, {"x": "2022 52", "y": 0}, '
            '{"x": "2023 1", "y": 0}, {"x": "2023 2", "y": 0}, {"x": "2023 3", "y": 0}, '
            '{"x": "2023 4", "y": 0}, {"x": "2023 5", "y": 0}, {"x": "2023 6", "y": 0}, '
            '{"x": "2023 7", "y": 0}, {"x": "2023 8", "y": 0}, {"x": "2023 9", "y": 0}, '
            '{"x": "2023 10", "y": 0}, {"x": "2023 11", "y": 0}, {"x": "2023 12", "y": 1}, '
            '{"x": "2023 13", "y": 0}, {"x": "2023 14", "y": 0}, {"x": "2023 15", "y": 0}, '
            '{"x": "2023 16", "y": 0}, {"x": "2023 17", "y": 0}, {"x": "2023 18", "y": 0}, '
            '{"x": "2023 19", "y": 0}, {"x": "2023 20", "y": 0}, {"x": "2023 21", "y": 0}, '
            '{"x": "2023 22", "y": 0}, {"x": "2023 23", "y": 0}, {"x": "2023 24", "y": 0}], '
            '"borderWidth": 1, "fill": true}]'
        ),
        "bar_chart_data_titles_counts": [
            (JUR1_LABEL, 2),
            (JUR2_LABEL, 1),
        ],
        "max_count": 2,
    },
    "duration-daily": {
        "time_chart_data": (
            '[{"label": "' + JUR1_LABEL + '", "data": ['
            '{"x": "2023 05 15", "y": 0}, {"x": "2023 05 16", "y": 0}, {"x": "2023 05 17", "y": 0}, '
            '{"x": "2023 05 18", "y": 0}, {"x": "2023 05 19", "y": 0}, {"x": "2023 05 20", "y": 0}, '
            '{"x": "2023 05 21", "y": 0}, {"x": "2023 05 22", "y": 0}, {"x": "2023 05 23", "y": 0}, '
            '{"x": "2023 05 24", "y": 0}, {"x": "2023 05 25", "y": 0}, {"x": "2023 05 26", "y": 0}, '
            '{"x": "2023 05 27", "y": 0}, {"x": "2023 05 28", "y": 0}, {"x": "2023 05 29", "y": 0}, '
            '{"x": "2023 05 30", "y": 0}, {"x": "2023 05 31", "y": 0}, {"x": "2023 06 01", "y": 0}, '
            '{"x": "2023 06 02", "y": 0}, {"x": "2023 06 03", "y": 0}, {"x": "2023 06 04", "y": 0}, '
            '{"x": "2023 06 05", "y": 0}, {"x": "2023 06 06", "y": 0}, {"x": "2023 06 07", "y": 0}, '
            '{"x": "2023 06 08", "y": 0}, {"x": "2023 06 09", "y": 0}, {"x": "2023 06 10", "y": 1}, '
            '{"x": "2023 06 11", "y": 0}, {"x": "2023 06 12", "y": 0}, {"x": "2023 06 13", "y": 0}, '
            '{"x": "2023 06 14", "y": 0}, {"x": "2023 06 15", "y": 0}], "borderWidth": 1, "fill": true}, '
            '{"label": "' + JUR2_LABEL + '", "data": ['
            '{"x": "2023 05 15", "y": 0}, {"x": "2023 05 16", "y": 0}, {"x": "2023 05 17", "y": 0}, '
            '{"x": "2023 05 18", "y": 0}, {"x": "2023 05 19", "y": 0}, {"x": "2023 05 20", "y": 0}, '
            '{"x": "2023 05 21", "y": 0}, {"x": "2023 05 22", "y": 0}, {"x": "2023 05 23", "y": 0}, '
            '{"x": "2023 05 24", "y": 0}, {"x": "2023 05 25", "y": 0}, {"x": "2023 05 26", "y": 0}, '
            '{"x": "2023 05 27", "y": 0}, {"x": "2023 05 28", "y": 0}, {"x": "2023 05 29", "y": 0}, '
            '{"x": "2023 05 30", "y": 0}, {"x": "2023 05 31", "y": 0}, {"x": "2023 06 01", "y": 0}, '
            '{"x": "2023 06 02", "y": 0}, {"x": "2023 06 03", "y": 0}, {"x": "2023 06 04", "y": 0}, '
            '{"x": "2023 06 05", "y": 0}, {"x": "2023 06 06", "y": 0}, {"x": "2023 06 07", "y": 0}, '
            '{"x": "2023 06 08", "y": 0}, {"x": "2023 06 09", "y": 0}, {"x": "2023 06 10", "y": 0}, '
            '{"x": "2023 06 11", "y": 0}, {"x": "2023 06 12", "y": 0}, {"x": "2023 06 13", "y": 0}, '
            '{"x": "2023 06 14", "y": 0}, {"x": "2023 06 15", "y": 0}], "borderWidth": 1, "fill": true}]'
        ),
        "bar_chart_data_titles_counts": [
            (JUR1_LABEL, 2),
            (JUR2_LABEL, 1),
        ],
        "max_count": 2,
    },
}


@pytest.fixture
def jur_org_data(db):
    jur1 = AreaOfManagement.objects.get(id=2)
    jur2 = AreaOfManagement.objects.get(id=3)

    org1 = OrganizationFactory(title="Org Alpha", jurisdiction=jur1)
    org1.created = timezone.datetime(2023, 6, 10, 10, 0, 0, tzinfo=timezone.utc)
    org1.save()

    org2 = OrganizationFactory(title="Org Beta", jurisdiction=jur1)
    org2.created = timezone.datetime(2022, 12, 5, 10, 0, 0, tzinfo=timezone.utc)
    org2.save()

    org3 = OrganizationFactory(title="Org Gamma", jurisdiction=jur2)
    org3.created = timezone.datetime(2023, 3, 20, 10, 0, 0, tzinfo=timezone.utc)
    org3.save()

    return [org1, org2, org3]


def _normalize_snapshot(snapshot):
    labels = {JUR1_LABEL, JUR2_LABEL}
    tcd = sorted(
        (series for series in json.loads(snapshot["time_chart_data"]) if series["label"] in labels),
        key=lambda x: x["label"],
    )
    bar = sorted((item for item in snapshot["bar_chart_data_titles_counts"] if item[0] in labels), key=lambda x: x[0])
    return {
        "time_chart_data": json.dumps(tcd, ensure_ascii=False),
        "bar_chart_data_titles_counts": bar,
        "max_count": snapshot["max_count"],
    }


@pytest.mark.django_db
@pytest.mark.parametrize("duration", DURATIONS)
def test_org_managements_stats_snapshot(jur_org_data, duration):
    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            OrganizationManagementsView,
            reverse("organization-stats-jurisdiction"),
            params={"indicator": "organization-count", "duration": duration},
        )
    assert ctx is not None

    tcd = ctx["time_chart_data"]
    bar_raw = ctx["bar_chart_data"]
    max_count = ctx["max_count"]

    parsed = tcd
    total_y = sum(pt["y"] for series in parsed for pt in series["data"])
    assert total_y > 0, f"Time series is all-zero for {duration}; fixture data may not land in the window"
    assert len(parsed) >= 2, f"Expected ≥2 jurisdiction series but got {len(parsed)}"

    snapshot = {
        "time_chart_data": json.dumps(tcd),
        "bar_chart_data_titles_counts": [(str(b["title"]), b["count"]) for b in bar_raw],
        "max_count": max_count,
    }

    assert _normalize_snapshot(snapshot) == _normalize_snapshot(EXPECTED[duration])


@pytest.mark.django_db
def test_org_managements_stats_query_count(jur_org_data):
    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            get_stats_context(
                OrganizationManagementsView,
                reverse("organization-stats-jurisdiction"),
                params={"indicator": "organization-count", "duration": "duration-daily"},
            )

    org_queries = [q for q in ctx.captured_queries if '"organization"' in q["sql"] and "SELECT" in q["sql"].upper()]
    assert len(org_queries) <= 10, (
        f"Expected ≤10 organization SELECT queries but got {len(org_queries)}. "
        f"The N+1 pattern may have been reintroduced (pre-refactor baseline: 64)."
    )
