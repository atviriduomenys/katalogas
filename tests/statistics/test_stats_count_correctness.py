import json

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from freezegun import freeze_time

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory

from tests.stats_utils import FROZEN_NOW


@pytest.fixture
def org_datasets_across_years(db):
    org = OrganizationFactory(title="Org Alpha")
    with freeze_time("2022-03-01"):
        for _ in range(3):
            DatasetFactory(organization=org)
    with freeze_time("2023-02-01"):
        for _ in range(2):
            DatasetFactory(organization=org)
    return org


@pytest.mark.haystack
@pytest.mark.django_db
def test_dataset_count_bar_chart_counts_all_org_datasets(app: DjangoTestApp, org_datasets_across_years):
    with freeze_time(FROZEN_NOW):
        resp = app.get(reverse("dataset-stats-organization"), params={"duration": "duration-yearly"})
    bar = resp.context["bar_chart_data"]
    assert [(str(b["display_value"]), b["count"]) for b in bar] == [("Org Alpha", 5)]


@pytest.mark.haystack
@pytest.mark.django_db
def test_dataset_count_bar_chart_includes_datasets_created_before_window(app: DjangoTestApp, db):
    org = OrganizationFactory(title="Org Beta")
    with freeze_time("2020-04-01"):
        DatasetFactory(organization=org)
    with freeze_time("2023-02-01"):
        DatasetFactory(organization=org)
    # the quarterly window only covers the last two years, the daily window
    # only the last month - the bar chart total must include older datasets
    for duration in ("duration-quarterly", "duration-daily"):
        with freeze_time(FROZEN_NOW):
            resp = app.get(reverse("dataset-stats-organization"), params={"duration": duration})
        bar = resp.context["bar_chart_data"]
        assert [(str(b["display_value"]), b["count"]) for b in bar] == [("Org Beta", 2)], duration


@pytest.mark.haystack
@pytest.mark.django_db
def test_dataset_count_bar_chart_includes_future_dated_datasets(app: DjangoTestApp, db):
    org = OrganizationFactory(title="Org Gamma")
    with freeze_time("2022-04-01"):
        DatasetFactory(organization=org)
    # created after the window end ("now"); the bar total must still match the
    # facet, which counts the dataset regardless of date
    with freeze_time("2024-08-01"):
        DatasetFactory(organization=org)
    with freeze_time(FROZEN_NOW):
        resp = app.get(reverse("dataset-stats-organization"), params={"duration": "duration-yearly"})
    bar = resp.context["bar_chart_data"]
    assert [(str(b["display_value"]), b["count"]) for b in bar] == [("Org Gamma", 2)]


@pytest.mark.haystack
@pytest.mark.django_db
def test_dataset_count_time_chart_counts_datasets_per_year(app: DjangoTestApp, org_datasets_across_years):
    with freeze_time(FROZEN_NOW):
        resp = app.get(reverse("dataset-stats-organization"), params={"duration": "duration-yearly"})
    series = json.loads(resp.context["time_chart_data"])
    assert len(series) == 1
    assert {point["x"]: point["y"] for point in series[0]["data"]} == {
        "2019": 0,
        "2020": 0,
        "2021": 0,
        "2022": 3,
        "2023": 2,
    }
