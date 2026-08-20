import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_webtest import DjangoTestApp
from hitcount.models import HitCount

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset


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


@pytest.mark.django_db
def test_landing_shows_the_real_hit_count(app: DjangoTestApp):
    dataset = DatasetFactory()
    HitCount.objects.create(
        content_type=ContentType.objects.get_for_model(Dataset),
        object_pk=dataset.pk,
        hits=3123,
    )

    response = app.get(reverse("home"))

    rendered = {row.dataset.pk: row for row in response.context["datasets"]}
    assert rendered[dataset.pk].hits == 3123
    assert "3123" in response.text
