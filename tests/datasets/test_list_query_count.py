import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory


@pytest.mark.django_db
def test_dataset_list_query_count_does_not_grow_with_result_count(app: DjangoTestApp):
    DatasetFactory.create_batch(3)
    app.get(reverse("dataset-list"))

    with CaptureQueriesContext(connection) as few:
        few_resp = app.get(reverse("dataset-list"))
    assert len(few_resp.context["object_list"]) == 3

    DatasetFactory.create_batch(12)
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
