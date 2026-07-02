from datetime import datetime, timezone

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from freezegun import freeze_time

from vitrina.comments.models import Comment
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.users.factories import UserFactory

from tests.stats_utils import FROZEN_NOW


def _status_comment(user, ct, dataset, status, created):
    comment = Comment.objects.create(
        user=user,
        content_type=ct,
        object_id=dataset.pk,
        status=status,
        body=f"{status}-{created.isoformat()}-{dataset.pk}",
        type=Comment.STATUS,
    )
    Comment.objects.filter(pk=comment.pk).update(created=created)
    return comment


@pytest.fixture
def datasets_with_overlapping_comment_times(db):
    ct = ContentType.objects.get_for_model(Dataset)
    user = UserFactory()

    # ds_open has an older comment whose timestamp equals ds_inv's latest
    # comment timestamp, so only a per-dataset (pairwise) latest-comment
    # lookup counts each dataset exactly once.
    ds_open = DatasetFactory(status=Dataset.HAS_DATA, slug="status-corr-open")
    ds_inv = DatasetFactory(status=Dataset.INVENTORED, slug="status-corr-inv")

    shared_moment = datetime(2022, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
    _status_comment(user, ct, ds_open, "OPENED", shared_moment)
    _status_comment(user, ct, ds_open, "OPENED", datetime(2023, 2, 1, 10, 0, 0, tzinfo=timezone.utc))
    _status_comment(user, ct, ds_inv, "INVENTORED", shared_moment)

    return [ds_open, ds_inv]


@pytest.mark.haystack
@pytest.mark.django_db
def test_status_chart_counts_each_dataset_once(app: DjangoTestApp, datasets_with_overlapping_comment_times):
    with freeze_time(FROZEN_NOW):
        resp = app.get(reverse("dataset-stats-status"), params={"duration": "duration-yearly"})
    counts = {str(b["display_value"]): b["count"] for b in resp.context["bar_chart_data"]}
    assert counts["Atverti duomenys"] == 1
    assert counts["Tik inventorinti"] == 1


def _yearly_series(resp):
    return {
        series["label"]: {point["x"]: point["y"] for point in series["data"]}
        for series in resp.context["time_chart_data"]
    }


@pytest.mark.haystack
@pytest.mark.django_db
def test_status_chart_counts_commentless_dataset_at_published_date(app: DjangoTestApp, db):
    DatasetFactory(
        status=Dataset.HAS_DATA,
        slug="status-corr-no-comment",
        published=datetime(2022, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    with freeze_time(FROZEN_NOW):
        resp = app.get(reverse("dataset-stats-status"), params={"duration": "duration-yearly"})
    counts = {str(b["display_value"]): b["count"] for b in resp.context["bar_chart_data"]}
    assert counts["Atverti duomenys"] == 1
    assert _yearly_series(resp)["Atverti duomenys"]["2022"] == 1


@pytest.mark.haystack
@pytest.mark.django_db
def test_status_chart_bar_includes_status_changes_before_window(app: DjangoTestApp, db):
    ct = ContentType.objects.get_for_model(Dataset)
    user = UserFactory()
    ds = DatasetFactory(status=Dataset.HAS_DATA, slug="status-corr-old-open")
    _status_comment(user, ct, ds, "OPENED", datetime(2020, 6, 1, 10, 0, 0, tzinfo=timezone.utc))

    for duration in ("duration-quarterly", "duration-daily"):
        with freeze_time(FROZEN_NOW):
            resp = app.get(reverse("dataset-stats-status"), params={"duration": duration})
        counts = {str(b["display_value"]): b["count"] for b in resp.context["bar_chart_data"]}
        assert counts["Atverti duomenys"] == 1, duration


@pytest.mark.haystack
@pytest.mark.django_db
def test_status_chart_falls_back_to_created_date_when_never_published(app: DjangoTestApp, db):
    with freeze_time("2021-03-01"):
        DatasetFactory(
            status=Dataset.INVENTORED,
            slug="status-corr-no-published",
            published=None,
        )
    with freeze_time(FROZEN_NOW):
        resp = app.get(reverse("dataset-stats-status"), params={"duration": "duration-yearly"})
    counts = {str(b["display_value"]): b["count"] for b in resp.context["bar_chart_data"]}
    assert counts["Tik inventorinti"] == 1
    assert _yearly_series(resp)["Tik inventorinti"]["2021"] == 1
