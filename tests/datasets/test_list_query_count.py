import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import CategoryFactory
from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory, UapiFormat
from vitrina.structure.factories import ModelFactory


def _plain_dataset():
    return DatasetFactory()


def _dataservice_dataset():
    """A dataset shaped like a Spinta/DSA one: a UAPI distribution and a structure model."""
    dataset = DatasetFactory()
    DatasetDistributionFactory(dataset=dataset, format=UapiFormat())
    ModelFactory(metadata_version__dataset=dataset)
    return dataset


def _categorised_dataset():
    root = CategoryFactory(title="Aplinka", icon="cloud-sun")
    category = root.get_children().first() or root.add_child(title="Oras", featured=False)
    return DatasetFactory(category=[category])


@pytest.mark.parametrize(
    "make_dataset",
    [_plain_dataset, _dataservice_dataset, _categorised_dataset],
    ids=["plain", "dataservice", "categorised"],
)
@pytest.mark.django_db
def test_dataset_list_query_count_does_not_grow_with_result_count(app: DjangoTestApp, make_dataset):
    for _ in range(3):
        make_dataset()
    app.get(reverse("dataset-list"))

    with CaptureQueriesContext(connection) as few:
        few_resp = app.get(reverse("dataset-list"))
    assert len(few_resp.context["object_list"]) == 3

    for _ in range(12):
        make_dataset()
    with CaptureQueriesContext(connection) as many:
        many_resp = app.get(reverse("dataset-list"))
    assert len(many_resp.context["object_list"]) == 15

    growth = len(many) - len(few)
    assert growth <= 2, f"{growth} extra queries for 12 extra results ({len(few)} -> {len(many)})"


@pytest.mark.django_db
def test_dataset_list_does_not_write_to_the_database(app: DjangoTestApp):
    DatasetFactory.create_batch(3)
    app.get(reverse("dataset-list"))
    DatasetFactory.create_batch(5)

    with CaptureQueriesContext(connection) as queries:
        app.get(reverse("dataset-list"))

    writes = [
        query["sql"]
        for query in queries.captured_queries
        if query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE"))
    ]
    assert writes == [], f"the list wrote {len(writes)} rows on a GET: {writes[:2]}"


@pytest.mark.django_db
def test_stats_view_query_count_does_not_grow_with_dataset_count(app: DjangoTestApp):
    DatasetFactory.create_batch(3)
    app.get(reverse("dataset-stats-jurisdiction"))

    with CaptureQueriesContext(connection) as few:
        app.get(reverse("dataset-stats-jurisdiction"))

    DatasetFactory.create_batch(12)
    with CaptureQueriesContext(connection) as many:
        app.get(reverse("dataset-stats-jurisdiction"))

    growth = len(many) - len(few)
    assert growth <= 2, f"{growth} extra queries for 12 extra datasets ({len(few)} -> {len(many)})"


def _set_tags(dataset, count, offset=0):
    dataset.tags = ", ".join(f"tag{index}" for index in range(offset, offset + count))
    dataset.save()


@pytest.mark.django_db
def test_dataset_list_query_count_does_not_grow_with_tag_count(app: DjangoTestApp):
    dataset = DatasetFactory()
    _set_tags(dataset, 3)
    app.get(reverse("dataset-list"))

    with CaptureQueriesContext(connection) as few:
        app.get(reverse("dataset-list"))

    _set_tags(dataset, 30)
    with CaptureQueriesContext(connection) as many:
        app.get(reverse("dataset-list"))

    growth = len(many) - len(few)
    assert growth <= 2, f"{growth} extra queries for 27 extra tags ({len(few)} -> {len(many)})"
