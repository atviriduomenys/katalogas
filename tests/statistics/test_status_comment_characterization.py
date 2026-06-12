import json
from datetime import datetime, timezone

import pytest
from django.contrib.contenttypes.models import ContentType
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django_webtest import DjangoTestApp
from freezegun import freeze_time

from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.users.factories import UserFactory

from tests.stats_utils import DURATIONS, FROZEN_NOW


@pytest.fixture
def comment_seeded_data(db):
    ct = ContentType.objects.get_for_model(Dataset)
    user = UserFactory()

    ds_has_data = DatasetFactory(status=Dataset.HAS_DATA, slug="comment-char-has-data")
    ds_inventored = DatasetFactory(status=Dataset.INVENTORED, slug="comment-char-inventored")
    ds_planned = DatasetFactory(status=Dataset.PLANNED, slug="comment-char-planned")

    for ds, comm_status, dt_early, dt_late in [
        (
            ds_has_data,
            "OPENED",
            datetime(2023, 1, 15, tzinfo=timezone.utc),
            datetime(2023, 2, 1, tzinfo=timezone.utc),
        ),
        (
            ds_inventored,
            "INVENTORED",
            datetime(2023, 2, 1, tzinfo=timezone.utc),
            datetime(2023, 3, 1, tzinfo=timezone.utc),
        ),
        (
            ds_planned,
            "PLANNED",
            datetime(2023, 3, 1, tzinfo=timezone.utc),
            datetime(2023, 4, 1, tzinfo=timezone.utc),
        ),
    ]:
        c_early = Comment.objects.create(
            user=user,
            content_type=ct,
            object_id=ds.pk,
            status=comm_status,
            body=f"early-{ds.slug}",
            type=Comment.STATUS,
        )
        Comment.objects.filter(pk=c_early.pk).update(created=dt_early)

        c_late = Comment.objects.create(
            user=user,
            content_type=ct,
            object_id=ds.pk,
            status=comm_status,
            body=f"late-{ds.slug}",
            type=Comment.STATUS,
        )
        Comment.objects.filter(pk=c_late.pk).update(created=dt_late)

    return [ds_has_data, ds_inventored, ds_planned]


EXPECTED = {
    "duration-yearly": {
        "time_chart_data": '[{"label": "Atverti duomenys", "data": [{"x": "2019", "y": 0}, {"x": "2020", "y": 0}, {"x": "2021", "y": 0}, {"x": "2022", "y": 0}, {"x": "2023", "y": 1}], "borderWidth": 1, "fill": true}, {"label": "Tik inventorinti", "data": [{"x": "2019", "y": 0}, {"x": "2020", "y": 0}, {"x": "2021", "y": 0}, {"x": "2022", "y": 0}, {"x": "2023", "y": 1}], "borderWidth": 1, "fill": true}, {"label": "Planuojama atverti", "data": [{"x": "2019", "y": 0}, {"x": "2020", "y": 0}, {"x": "2021", "y": 0}, {"x": "2022", "y": 0}, {"x": "2023", "y": 1}], "borderWidth": 1, "fill": true}]',
        "bar_chart_data": [
            {"display_value": "Atverti duomenys", "count": 1},
            {"display_value": "Tik inventorinti", "count": 1},
            {"display_value": "Planuojama atverti", "count": 1},
        ],
        "max_count": 1,
    },
    "duration-quarterly": {
        "time_chart_data": '[{"label": "Planuojama atverti", "data": [{"x": "2021 Bir", "y": 0}, {"x": "2021 Rugs", "y": 0}, {"x": "2021 Grd", "y": 0}, {"x": "2022 Kov", "y": 0}, {"x": "2022 Bir", "y": 0}, {"x": "2022 Rugs", "y": 0}, {"x": "2022 Grd", "y": 0}, {"x": "2023 Kov", "y": 0}, {"x": "2023 Bir", "y": 1}], "borderWidth": 1, "fill": true}, {"label": "Atverti duomenys", "data": [{"x": "2021 Bir", "y": 0}, {"x": "2021 Rugs", "y": 0}, {"x": "2021 Grd", "y": 0}, {"x": "2022 Kov", "y": 0}, {"x": "2022 Bir", "y": 0}, {"x": "2022 Rugs", "y": 0}, {"x": "2022 Grd", "y": 0}, {"x": "2023 Kov", "y": 1}, {"x": "2023 Bir", "y": 0}], "borderWidth": 1, "fill": true}, {"label": "Tik inventorinti", "data": [{"x": "2021 Bir", "y": 0}, {"x": "2021 Rugs", "y": 0}, {"x": "2021 Grd", "y": 0}, {"x": "2022 Kov", "y": 0}, {"x": "2022 Bir", "y": 0}, {"x": "2022 Rugs", "y": 0}, {"x": "2022 Grd", "y": 0}, {"x": "2023 Kov", "y": 1}, {"x": "2023 Bir", "y": 0}], "borderWidth": 1, "fill": true}]',
        "bar_chart_data": [
            {"display_value": "Atverti duomenys", "count": 1},
            {"display_value": "Tik inventorinti", "count": 1},
            {"display_value": "Planuojama atverti", "count": 1},
        ],
        "max_count": 1,
    },
    "duration-monthly": {
        "time_chart_data": '[{"label": "Atverti duomenys", "data": [{"x": "2022 06", "y": 0}, {"x": "2022 07", "y": 0}, {"x": "2022 08", "y": 0}, {"x": "2022 09", "y": 0}, {"x": "2022 10", "y": 0}, {"x": "2022 11", "y": 0}, {"x": "2022 12", "y": 0}, {"x": "2023 01", "y": 0}, {"x": "2023 02", "y": 1}, {"x": "2023 03", "y": 0}, {"x": "2023 04", "y": 0}, {"x": "2023 05", "y": 0}, {"x": "2023 06", "y": 0}], "borderWidth": 1, "fill": true}, {"label": "Tik inventorinti", "data": [{"x": "2022 06", "y": 0}, {"x": "2022 07", "y": 0}, {"x": "2022 08", "y": 0}, {"x": "2022 09", "y": 0}, {"x": "2022 10", "y": 0}, {"x": "2022 11", "y": 0}, {"x": "2022 12", "y": 0}, {"x": "2023 01", "y": 0}, {"x": "2023 02", "y": 0}, {"x": "2023 03", "y": 1}, {"x": "2023 04", "y": 0}, {"x": "2023 05", "y": 0}, {"x": "2023 06", "y": 0}], "borderWidth": 1, "fill": true}, {"label": "Planuojama atverti", "data": [{"x": "2022 06", "y": 0}, {"x": "2022 07", "y": 0}, {"x": "2022 08", "y": 0}, {"x": "2022 09", "y": 0}, {"x": "2022 10", "y": 0}, {"x": "2022 11", "y": 0}, {"x": "2022 12", "y": 0}, {"x": "2023 01", "y": 0}, {"x": "2023 02", "y": 0}, {"x": "2023 03", "y": 0}, {"x": "2023 04", "y": 1}, {"x": "2023 05", "y": 0}, {"x": "2023 06", "y": 0}], "borderWidth": 1, "fill": true}]',
        "bar_chart_data": [
            {"display_value": "Atverti duomenys", "count": 1},
            {"display_value": "Tik inventorinti", "count": 1},
            {"display_value": "Planuojama atverti", "count": 1},
        ],
        "max_count": 1,
    },
    "duration-weekly": {
        "time_chart_data": '[{"label": "Atverti duomenys", "data": [{"x": "2022 50", "y": 0}, {"x": "2022 51", "y": 0}, {"x": "2022 52", "y": 0}, {"x": "2023 1", "y": 0}, {"x": "2023 2", "y": 0}, {"x": "2023 3", "y": 0}, {"x": "2023 4", "y": 0}, {"x": "2023 5", "y": 1}, {"x": "2023 6", "y": 0}, {"x": "2023 7", "y": 0}, {"x": "2023 8", "y": 0}, {"x": "2023 9", "y": 0}, {"x": "2023 10", "y": 0}, {"x": "2023 11", "y": 0}, {"x": "2023 12", "y": 0}, {"x": "2023 13", "y": 0}, {"x": "2023 14", "y": 0}, {"x": "2023 15", "y": 0}, {"x": "2023 16", "y": 0}, {"x": "2023 17", "y": 0}, {"x": "2023 18", "y": 0}, {"x": "2023 19", "y": 0}, {"x": "2023 20", "y": 0}, {"x": "2023 21", "y": 0}, {"x": "2023 22", "y": 0}, {"x": "2023 23", "y": 0}, {"x": "2023 24", "y": 0}], "borderWidth": 1, "fill": true}, {"label": "Tik inventorinti", "data": [{"x": "2022 50", "y": 0}, {"x": "2022 51", "y": 0}, {"x": "2022 52", "y": 0}, {"x": "2023 1", "y": 0}, {"x": "2023 2", "y": 0}, {"x": "2023 3", "y": 0}, {"x": "2023 4", "y": 0}, {"x": "2023 5", "y": 0}, {"x": "2023 6", "y": 0}, {"x": "2023 7", "y": 0}, {"x": "2023 8", "y": 0}, {"x": "2023 9", "y": 1}, {"x": "2023 10", "y": 0}, {"x": "2023 11", "y": 0}, {"x": "2023 12", "y": 0}, {"x": "2023 13", "y": 0}, {"x": "2023 14", "y": 0}, {"x": "2023 15", "y": 0}, {"x": "2023 16", "y": 0}, {"x": "2023 17", "y": 0}, {"x": "2023 18", "y": 0}, {"x": "2023 19", "y": 0}, {"x": "2023 20", "y": 0}, {"x": "2023 21", "y": 0}, {"x": "2023 22", "y": 0}, {"x": "2023 23", "y": 0}, {"x": "2023 24", "y": 0}], "borderWidth": 1, "fill": true}, {"label": "Planuojama atverti", "data": [{"x": "2022 50", "y": 0}, {"x": "2022 51", "y": 0}, {"x": "2022 52", "y": 0}, {"x": "2023 1", "y": 0}, {"x": "2023 2", "y": 0}, {"x": "2023 3", "y": 0}, {"x": "2023 4", "y": 0}, {"x": "2023 5", "y": 0}, {"x": "2023 6", "y": 0}, {"x": "2023 7", "y": 0}, {"x": "2023 8", "y": 0}, {"x": "2023 9", "y": 0}, {"x": "2023 10", "y": 0}, {"x": "2023 11", "y": 0}, {"x": "2023 12", "y": 0}, {"x": "2023 13", "y": 1}, {"x": "2023 14", "y": 0}, {"x": "2023 15", "y": 0}, {"x": "2023 16", "y": 0}, {"x": "2023 17", "y": 0}, {"x": "2023 18", "y": 0}, {"x": "2023 19", "y": 0}, {"x": "2023 20", "y": 0}, {"x": "2023 21", "y": 0}, {"x": "2023 22", "y": 0}, {"x": "2023 23", "y": 0}, {"x": "2023 24", "y": 0}], "borderWidth": 1, "fill": true}]',
        "bar_chart_data": [
            {"display_value": "Atverti duomenys", "count": 1},
            {"display_value": "Tik inventorinti", "count": 1},
            {"display_value": "Planuojama atverti", "count": 1},
        ],
        "max_count": 1,
    },
    "duration-daily": {
        "time_chart_data": '[{"label": "Atverti duomenys", "data": [{"x": "2023 05 15", "y": 0}, {"x": "2023 05 16", "y": 0}, {"x": "2023 05 17", "y": 0}, {"x": "2023 05 18", "y": 0}, {"x": "2023 05 19", "y": 0}, {"x": "2023 05 20", "y": 0}, {"x": "2023 05 21", "y": 0}, {"x": "2023 05 22", "y": 0}, {"x": "2023 05 23", "y": 0}, {"x": "2023 05 24", "y": 0}, {"x": "2023 05 25", "y": 0}, {"x": "2023 05 26", "y": 0}, {"x": "2023 05 27", "y": 0}, {"x": "2023 05 28", "y": 0}, {"x": "2023 05 29", "y": 0}, {"x": "2023 05 30", "y": 0}, {"x": "2023 05 31", "y": 0}, {"x": "2023 06 01", "y": 0}, {"x": "2023 06 02", "y": 0}, {"x": "2023 06 03", "y": 0}, {"x": "2023 06 04", "y": 0}, {"x": "2023 06 05", "y": 0}, {"x": "2023 06 06", "y": 0}, {"x": "2023 06 07", "y": 0}, {"x": "2023 06 08", "y": 0}, {"x": "2023 06 09", "y": 0}, {"x": "2023 06 10", "y": 0}, {"x": "2023 06 11", "y": 0}, {"x": "2023 06 12", "y": 0}, {"x": "2023 06 13", "y": 0}, {"x": "2023 06 14", "y": 0}, {"x": "2023 06 15", "y": 0}], "borderWidth": 1, "fill": true}, {"label": "Tik inventorinti", "data": [{"x": "2023 05 15", "y": 0}, {"x": "2023 05 16", "y": 0}, {"x": "2023 05 17", "y": 0}, {"x": "2023 05 18", "y": 0}, {"x": "2023 05 19", "y": 0}, {"x": "2023 05 20", "y": 0}, {"x": "2023 05 21", "y": 0}, {"x": "2023 05 22", "y": 0}, {"x": "2023 05 23", "y": 0}, {"x": "2023 05 24", "y": 0}, {"x": "2023 05 25", "y": 0}, {"x": "2023 05 26", "y": 0}, {"x": "2023 05 27", "y": 0}, {"x": "2023 05 28", "y": 0}, {"x": "2023 05 29", "y": 0}, {"x": "2023 05 30", "y": 0}, {"x": "2023 05 31", "y": 0}, {"x": "2023 06 01", "y": 0}, {"x": "2023 06 02", "y": 0}, {"x": "2023 06 03", "y": 0}, {"x": "2023 06 04", "y": 0}, {"x": "2023 06 05", "y": 0}, {"x": "2023 06 06", "y": 0}, {"x": "2023 06 07", "y": 0}, {"x": "2023 06 08", "y": 0}, {"x": "2023 06 09", "y": 0}, {"x": "2023 06 10", "y": 0}, {"x": "2023 06 11", "y": 0}, {"x": "2023 06 12", "y": 0}, {"x": "2023 06 13", "y": 0}, {"x": "2023 06 14", "y": 0}, {"x": "2023 06 15", "y": 0}], "borderWidth": 1, "fill": true}, {"label": "Planuojama atverti", "data": [{"x": "2023 05 15", "y": 0}, {"x": "2023 05 16", "y": 0}, {"x": "2023 05 17", "y": 0}, {"x": "2023 05 18", "y": 0}, {"x": "2023 05 19", "y": 0}, {"x": "2023 05 20", "y": 0}, {"x": "2023 05 21", "y": 0}, {"x": "2023 05 22", "y": 0}, {"x": "2023 05 23", "y": 0}, {"x": "2023 05 24", "y": 0}, {"x": "2023 05 25", "y": 0}, {"x": "2023 05 26", "y": 0}, {"x": "2023 05 27", "y": 0}, {"x": "2023 05 28", "y": 0}, {"x": "2023 05 29", "y": 0}, {"x": "2023 05 30", "y": 0}, {"x": "2023 05 31", "y": 0}, {"x": "2023 06 01", "y": 0}, {"x": "2023 06 02", "y": 0}, {"x": "2023 06 03", "y": 0}, {"x": "2023 06 04", "y": 0}, {"x": "2023 06 05", "y": 0}, {"x": "2023 06 06", "y": 0}, {"x": "2023 06 07", "y": 0}, {"x": "2023 06 08", "y": 0}, {"x": "2023 06 09", "y": 0}, {"x": "2023 06 10", "y": 0}, {"x": "2023 06 11", "y": 0}, {"x": "2023 06 12", "y": 0}, {"x": "2023 06 13", "y": 0}, {"x": "2023 06 14", "y": 0}, {"x": "2023 06 15", "y": 0}], "borderWidth": 1, "fill": true}]',
        "bar_chart_data": [
            {"display_value": "Atverti duomenys", "count": 0},
            {"display_value": "Tik inventorinti", "count": 0},
            {"display_value": "Planuojama atverti", "count": 0},
        ],
        "max_count": 0,
    },
}


def _normalize_bar_chart(bar_chart_data):
    return sorted(
        [{"display_value": str(b.get("display_value")), "count": b.get("count")} for b in bar_chart_data],
        key=lambda x: x["display_value"],
    )


@pytest.mark.haystack
@pytest.mark.django_db
@pytest.mark.parametrize("duration", DURATIONS)
def test_status_comment_snapshot(app: DjangoTestApp, comment_seeded_data, duration):
    with freeze_time(FROZEN_NOW):
        resp = app.get(
            reverse("dataset-stats-status"),
            params={"indicator": "dataset-count", "duration": duration},
        )
    assert resp.status_code == 200

    snapshot = {
        "time_chart_data": resp.context["time_chart_data"],
        "bar_chart_data": _normalize_bar_chart(resp.context["bar_chart_data"]),
        "max_count": resp.context["max_count"],
    }
    expected = {
        "time_chart_data": EXPECTED[duration]["time_chart_data"],
        "bar_chart_data": _normalize_bar_chart(EXPECTED[duration]["bar_chart_data"]),
        "max_count": EXPECTED[duration]["max_count"],
    }

    assert snapshot == expected

    if duration == "duration-yearly":
        chart = json.loads(resp.context["time_chart_data"])
        all_y = [pt["y"] for series in chart for pt in series["data"]]
        assert any(y > 0 for y in all_y), "Branch B produced no non-zero counts — seeding may be wrong"


@pytest.mark.haystack
@pytest.mark.django_db
def test_query_count_guard(app: DjangoTestApp, comment_seeded_data):
    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            resp = app.get(
                reverse("dataset-stats-status"),
                params={"indicator": "dataset-count", "duration": "duration-daily"},
            )

    assert resp.status_code == 200

    comment_queries = [q for q in ctx.captured_queries if "vitrina_comments_comment" in q["sql"]]
    assert len(comment_queries) < 10, (
        f"Too many comment queries ({len(comment_queries)}): N+1 not fixed. "
        f"Queries: {[q['sql'][:120] for q in comment_queries]}"
    )
