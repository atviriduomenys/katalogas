import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun import freeze_time

from vitrina.classifiers.factories import CategoryFactory
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.views import CategoryStatsView
from vitrina.orgs.factories import OrganizationFactory
from vitrina.statistics.factories import DatasetStatsFactory, ModelDownloadStatsFactory
from vitrina.structure.factories import MetadataFactory, ModelFactory, VersionFactory

from tests.stats_utils import FROZEN_NOW, get_stats_context

INDICATORS = ["dataset-count", "object-count", "request-count"]

EXPECTED = {
    "dataset-count": {
        "max_count": 2,
        "active_filter": "category",
        "active_indicator": "dataset-count",
        "sort": "sort-desc",
        "category_data_stats": None,
        "category_data_counts": [2, 1],
    },
    "object-count": {
        "max_count": 30,
        "active_filter": "category",
        "active_indicator": "object-count",
        "sort": "sort-desc",
        "category_data_stats": [30, 15],
        "category_data_counts": [2, 1],
    },
    "request-count": {
        "max_count": 13,
        "active_filter": "category",
        "active_indicator": "request-count",
        "sort": "sort-desc",
        "category_data_stats": [13, 7],
        "category_data_counts": [2, 1],
    },
}


@pytest.fixture
def category_stats_data(db):
    org = OrganizationFactory()

    parent_cat = CategoryFactory(title="Parent Cat Stats")
    child_a = parent_cat.add_child(
        instance=CategoryFactory.build(title="Child Cat A"),
    )
    child_b = parent_cat.add_child(
        instance=CategoryFactory.build(title="Child Cat B"),
    )
    child_c = parent_cat.add_child(
        instance=CategoryFactory.build(title="Child Cat C"),
    )

    ds_a1 = DatasetFactory(slug="ds-a1-cat", organization=org)
    ds_a1.category.add(child_a)
    ds_a1.save()

    ds_a2 = DatasetFactory(slug="ds-a2-cat", organization=org)
    ds_a2.category.add(child_a)
    ds_a2.save()

    ds_b = DatasetFactory(slug="ds-b-cat", organization=org)
    ds_b.category.add(child_b)
    ds_b.save()

    DatasetStatsFactory(dataset_id=ds_a1.pk, object_count=10, request_count=5, maturity_level=3)
    DatasetStatsFactory(dataset_id=ds_a2.pk, object_count=20, request_count=8, maturity_level=4)
    DatasetStatsFactory(dataset_id=ds_b.pk, object_count=15, request_count=7, maturity_level=2)

    return parent_cat, child_a, child_b, child_c, ds_a1, ds_a2, ds_b


@pytest.mark.django_db
@pytest.mark.parametrize("indicator", INDICATORS)
def test_category_stats_snapshot(category_stats_data, indicator):
    parent_cat, child_a, child_b, child_c, ds_a1, ds_a2, ds_b = category_stats_data

    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            CategoryStatsView,
            reverse("dataset-stats-category-children", kwargs={"pk": parent_cat.pk}),
            params={"indicator": indicator, "sort": "sort-desc"},
            pk=parent_cat.pk,
        )
    assert ctx is not None

    expected = EXPECTED[indicator]

    cat_data = ctx["category_data"]

    assert any(d["count"] > 0 for d in cat_data), (
        f"All ES counts are zero for indicator={indicator}; fixture may not be indexed correctly"
    )
    assert len(cat_data) == 2, f"Expected 2 child categories (child_c absent from ES) but got {len(cat_data)}"

    assert ctx["max_count"] == expected["max_count"]
    assert ctx["current_object"] == parent_cat.pk
    assert ctx["active_filter"] == expected["active_filter"]
    assert ctx["active_indicator"] == expected["active_indicator"]
    assert ctx["sort"] == expected["sort"]

    assert [d["count"] for d in cat_data] == expected["category_data_counts"], (
        f"ES counts mismatch for indicator={indicator}: got {[d['count'] for d in cat_data]}"
    )

    if indicator != "dataset-count":
        stats_values = [d.get("stats") for d in cat_data]
        assert stats_values == expected["category_data_stats"], (
            f"Stats values mismatch for indicator={indicator}: got {stats_values}"
        )
        assert all(v is not None and v > 0 for v in stats_values), (
            f"Expected all visible category stats > 0 for indicator={indicator}, got {stats_values}"
        )

    required_keys = {"filter_value", "display_value", "count", "url"}
    for d in cat_data:
        for key in required_keys:
            assert key in d, f"Missing key {key!r} in category_data entry: {d}"


@pytest.mark.django_db
def test_category_stats_query_count(category_stats_data):
    parent_cat, *_ = category_stats_data

    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            get_stats_context(
                CategoryStatsView,
                reverse("dataset-stats-category-children", kwargs={"pk": parent_cat.pk}),
                params={"indicator": "object-count", "sort": "sort-desc"},
                pk=parent_cat.pk,
            )

    stats_queries = [
        q for q in ctx.captured_queries if "dataset_statistic" in q["sql"] and "SELECT" in q["sql"].upper()
    ]
    assert len(stats_queries) <= 1, (
        f"Expected ≤1 dataset_statistic SELECT queries but got {len(stats_queries)}. "
        f"The N+1 pattern may have been reintroduced (pre-refactor baseline: 2)."
    )


DOWNLOAD_EXPECTED = {
    "download-request-count": [180, 10],
    "download-object-count": [1800, 100],
}


@pytest.fixture
def category_download_stats_data(db):
    org = OrganizationFactory()

    parent_cat = CategoryFactory(title="Parent DL Cat")
    child_a = parent_cat.add_child(instance=CategoryFactory.build(title="DL Child A"))
    child_b = parent_cat.add_child(instance=CategoryFactory.build(title="DL Child B"))

    ds_a1 = DatasetFactory(slug="ds-a1-dl", organization=org)
    ds_a1.category.add(child_a)
    ds_a1.save()

    ds_a2 = DatasetFactory(slug="ds-a2-dl", organization=org)
    ds_a2.category.add(child_a)
    ds_a2.save()

    ds_b = DatasetFactory(slug="ds-b-dl", organization=org)
    ds_b.category.add(child_b)
    ds_b.save()

    def add_model(dataset, name, model_requests, model_objects):
        version = VersionFactory(dataset=dataset)
        model = ModelFactory(metadata_version=version, dataset=dataset)
        MetadataFactory(object=model, dataset=dataset, name=name)
        ModelDownloadStatsFactory(model=name, model_requests=model_requests, model_objects=model_objects)

    add_model(ds_a1, "datasets/gov/dl/a1/Model1", 100, 1000)
    add_model(ds_a1, "datasets/gov/dl/a1/Model2", 50, 500)
    add_model(ds_a2, "datasets/gov/dl/a2/Model1", 30, 300)
    add_model(ds_b, "datasets/gov/dl/b/Model1", 10, 100)

    return parent_cat, child_a, child_b


@pytest.mark.django_db
@pytest.mark.parametrize("indicator", ["download-request-count", "download-object-count"])
def test_category_download_stats_snapshot(category_download_stats_data, indicator):
    parent_cat, child_a, child_b = category_download_stats_data

    with freeze_time(FROZEN_NOW):
        ctx = get_stats_context(
            CategoryStatsView,
            reverse("dataset-stats-category-children", kwargs={"pk": parent_cat.pk}),
            params={"indicator": indicator, "sort": "sort-desc"},
            pk=parent_cat.pk,
        )

    cat_data = ctx["category_data"]
    assert len(cat_data) == 2, f"Expected 2 child categories but got {len(cat_data)}"
    assert [d.get("stats") for d in cat_data] == DOWNLOAD_EXPECTED[indicator], (
        f"Download stats mismatch for indicator={indicator}: got {[d.get('stats') for d in cat_data]}"
    )
    assert ctx["active_indicator"] == indicator


@pytest.mark.django_db
def test_category_download_stats_query_count(category_download_stats_data):
    parent_cat, *_ = category_download_stats_data

    with freeze_time(FROZEN_NOW):
        with CaptureQueriesContext(connection) as ctx:
            get_stats_context(
                CategoryStatsView,
                reverse("dataset-stats-category-children", kwargs={"pk": parent_cat.pk}),
                params={"indicator": "download-request-count", "sort": "sort-desc"},
                pk=parent_cat.pk,
            )

    download_queries = [
        q for q in ctx.captured_queries if "model_download_statistic" in q["sql"] and "SELECT" in q["sql"].upper()
    ]
    assert len(download_queries) <= 2, (
        f"Expected ≤2 model_download_statistic SELECTs (one aggregate per visible category) "
        f"but got {len(download_queries)}; the per-model N+1 may have returned (pre-refactor baseline: 4)."
    )
