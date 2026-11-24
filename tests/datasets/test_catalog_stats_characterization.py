from datetime import timedelta, datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun import freeze_time

from vitrina.datasets.factories import (
    DatasetFactory,
    DCATResourceSubclassFactory,
    RelationFactory,
    DatasetRelationFactory,
)
from vitrina.datasets.models import DCATResourceSubclass, Relation
from vitrina.datasets.views import DatasetsCatalogsView
from vitrina.orgs.factories import OrganizationFactory
from vitrina.statistics.factories import DatasetStatsFactory, ModelDownloadStatsFactory

from tests.stats_utils import FROZEN_NOW, get_stats_context
from vitrina.structure.factories import VersionFactory, ModelFactory, MetadataFactory

INDICATORS = ["dataset-count", "object-count", "request-count"]

EXPECTED = {
    "dataset-count": {
        "max_count": 2,
        "active_filter": "catalog",
        "active_indicator": "dataset-count",
        "sort": "sort-desc",
        "catalog_data_stats": None,
        "catalog_data_counts": [2, 1],
    },
    "object-count": {
        "max_count": 30,
        "active_filter": "catalog",
        "active_indicator": "object-count",
        "sort": "sort-desc",
        "catalog_data_stats": [30, 15],
        "catalog_data_counts": [30, 15],
    },
    "request-count": {
        "max_count": 13,
        "active_filter": "catalog",
        "active_indicator": "request-count",
        "sort": "sort-desc",
        "catalog_data_stats": [13, 7],
        "catalog_data_counts": [13, 7],
    },
}

STATS_DATE = datetime.fromisoformat(FROZEN_NOW) - timedelta(days=30)


@pytest.fixture
def catalog_stats_data(db):
    organization = OrganizationFactory()
    catalog_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)
    dataset_subclass = DCATResourceSubclassFactory()
    catalog_a = DatasetFactory(organization=organization, subclass=catalog_subclass)
    catalog_b = DatasetFactory(organization=organization, subclass=catalog_subclass)

    ds_a1 = DatasetFactory(slug="ds-a1-catalog", organization=organization, subclass=dataset_subclass)
    ds_a2 = DatasetFactory(slug="ds-a2-catalog", organization=organization, subclass=dataset_subclass)
    ds_b = DatasetFactory(slug="ds-b-catalog", organization=organization, subclass=dataset_subclass)

    relation = RelationFactory(name=Relation.CATALOG)
    DatasetRelationFactory(relation=relation, dataset=ds_a1, part_of=catalog_a)
    DatasetRelationFactory(relation=relation, dataset=ds_a2, part_of=catalog_a)
    DatasetRelationFactory(relation=relation, dataset=ds_b, part_of=catalog_b)

    ds_a1.save()
    ds_a2.save()
    ds_b.save()

    DatasetStatsFactory(dataset_id=ds_a1.pk, object_count=10, request_count=5, maturity_level=3, created=STATS_DATE)
    DatasetStatsFactory(dataset_id=ds_a2.pk, object_count=20, request_count=8, maturity_level=4, created=STATS_DATE)
    DatasetStatsFactory(dataset_id=ds_b.pk, object_count=15, request_count=7, maturity_level=2, created=STATS_DATE)

    return catalog_a, catalog_b, ds_a1, ds_a2, ds_b


@pytest.mark.django_db
@pytest.mark.parametrize("indicator", INDICATORS)
def test_catalog_stats_snapshot(catalog_stats_data, indicator):
    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            DatasetsCatalogsView,
            reverse("dataset-stats-catalog"),
            params={"indicator": indicator, "sort": "sort-desc"},
        )

    expected = EXPECTED[indicator]
    catalog_data = ctx["bar_chart_data"]

    assert len(catalog_data) == 2
    assert any(d["count"] > 0 for d in catalog_data)

    assert ctx["max_count"] == expected["max_count"]
    assert ctx["active_filter"] == expected["active_filter"]
    assert ctx["active_indicator"] == expected["active_indicator"]
    assert ctx["sort"] == expected["sort"]

    assert [d["count"] for d in catalog_data] == expected["catalog_data_counts"]

    if indicator != "dataset-count":
        stats_values = [d["count"] for d in catalog_data]
        assert stats_values == expected["catalog_data_stats"]

    required_keys = {"filter_value", "display_value", "count", "url"}

    for d in catalog_data:
        for key in required_keys:
            assert key in d


@pytest.mark.django_db
def test_catalog_stats_query_count(catalog_stats_data):
    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            get_stats_context(
                DatasetsCatalogsView,
                reverse("dataset-stats-catalog"),
                params={"indicator": "object-count", "sort": "sort-desc"},
            )

    stats_queries = [
        q for q in ctx.captured_queries if "dataset_statistic" in q["sql"] and "SELECT" in q["sql"].upper()
    ]

    assert len(stats_queries) <= 2, f"Expected ≤2 dataset_statistic SELECT queries but got {len(stats_queries)}."


DOWNLOAD_EXPECTED = {
    "download-request-count": [180, 10],
    "download-object-count": [1800, 100],
}


@pytest.fixture
def catalog_download_stats_data(db):
    organization = OrganizationFactory()

    catalog_subclass = DCATResourceSubclassFactory(name=DCATResourceSubclass.CATALOG)
    dataset_subclass = DCATResourceSubclassFactory()
    catalog_a = DatasetFactory(organization=organization, subclass=catalog_subclass)
    catalog_b = DatasetFactory(organization=organization, subclass=catalog_subclass)

    ds_a1 = DatasetFactory(slug="ds-a1-dl", organization=organization, subclass=dataset_subclass)
    ds_a2 = DatasetFactory(slug="ds-a2-dl", organization=organization, subclass=dataset_subclass)
    ds_b = DatasetFactory(slug="ds-b-dl", organization=organization, subclass=dataset_subclass)

    relation = RelationFactory(name=Relation.CATALOG)

    DatasetRelationFactory(relation=relation, dataset=ds_a1, part_of=catalog_a)
    DatasetRelationFactory(relation=relation, dataset=ds_a2, part_of=catalog_a)
    DatasetRelationFactory(relation=relation, dataset=ds_b, part_of=catalog_b)

    ds_a1.save()
    ds_a2.save()
    ds_b.save()

    def add_model(dataset, name, model_requests, model_objects):
        version = VersionFactory(dataset=dataset)
        model = ModelFactory(metadata_version=version, dataset=dataset)
        MetadataFactory(object=model, dataset=dataset, name=name)
        ModelDownloadStatsFactory(
            model=name,
            model_requests=model_requests,
            model_objects=model_objects,
            created=STATS_DATE,
        )

    add_model(ds_a1, "datasets/gov/dl/a1/Model1", 100, 1000)
    add_model(ds_a1, "datasets/gov/dl/a1/Model2", 50, 500)
    add_model(ds_a2, "datasets/gov/dl/a2/Model1", 30, 300)
    add_model(ds_b, "datasets/gov/dl/b/Model1", 10, 100)

    return catalog_a, catalog_b


@pytest.mark.django_db
@pytest.mark.parametrize(
    "indicator",
    ["download-request-count", "download-object-count"],
)
def test_catalog_download_stats_snapshot(catalog_download_stats_data, indicator):
    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            DatasetsCatalogsView,
            reverse("dataset-stats-catalog"),
            params={"indicator": indicator, "sort": "sort-desc"},
        )

    catalog_data = ctx["bar_chart_data"]

    assert len(catalog_data) == 2

    stats_values = [d["count"] for d in catalog_data]

    assert stats_values == DOWNLOAD_EXPECTED[indicator]
    assert ctx["active_indicator"] == indicator


@pytest.mark.django_db
def test_catalog_download_stats_query_count(catalog_download_stats_data):
    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            get_stats_context(
                DatasetsCatalogsView,
                reverse("dataset-stats-catalog"),
                params={"indicator": "download-request-count", "sort": "sort-desc"},
            )

    download_queries = [
        q for q in ctx.captured_queries if "model_download_statistic" in q["sql"] and "SELECT" in q["sql"].upper()
    ]

    assert len(download_queries) <= 2, f"Expected ≤2 model_download_statistic SELECTs but got {len(download_queries)}."
