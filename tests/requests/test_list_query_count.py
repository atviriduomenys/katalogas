import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.requests.factories import RequestFactory


@pytest.mark.django_db
def test_request_list_query_count_does_not_grow_with_result_count(app: DjangoTestApp):
    RequestFactory.create_batch(3)
    app.get(reverse("request-list"))

    with CaptureQueriesContext(connection) as few:
        few_resp = app.get(reverse("request-list"))
    assert len(few_resp.context["object_list"]) == 3

    RequestFactory.create_batch(12)
    with CaptureQueriesContext(connection) as many:
        many_resp = app.get(reverse("request-list"))
    assert len(many_resp.context["object_list"]) == 15

    growth = len(many) - len(few)
    assert growth <= 2, f"{growth} extra queries for 12 extra results ({len(few)} -> {len(many)})"
