import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory


@pytest.mark.django_db
def test_landing_does_not_write_to_the_database(app: DjangoTestApp):
    app.get(reverse("home"))
    DatasetFactory.create_batch(3)

    with CaptureQueriesContext(connection) as queries:
        app.get(reverse("home"))

    writes = [
        query["sql"]
        for query in queries.captured_queries
        if query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE"))
    ]
    assert writes == [], f"the landing page wrote {len(writes)} rows on a GET: {writes[:2]}"
