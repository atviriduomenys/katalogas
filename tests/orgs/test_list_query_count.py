import pytest
from django.db import connection
from django.db.models import Max
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.models import AreaOfManagement
from vitrina.orgs.factories import OrganizationFactory


def _organizations_in_new_jurisdictions(count):
    for _ in range(count):
        next_id = (AreaOfManagement.objects.aggregate(top=Max("id"))["top"] or 0) + 1
        jurisdiction = AreaOfManagement.objects.create(
            id=next_id,
            name_lt=f"Sritis {next_id}",
            name_en=f"Area {next_id}",
        )
        OrganizationFactory(jurisdiction=jurisdiction)


@pytest.mark.django_db
def test_organization_list_query_count_does_not_grow_with_jurisdiction_count(app: DjangoTestApp):
    _organizations_in_new_jurisdictions(2)
    app.get(reverse("organization-list"))

    with CaptureQueriesContext(connection) as few:
        app.get(reverse("organization-list"))

    _organizations_in_new_jurisdictions(10)
    with CaptureQueriesContext(connection) as many:
        app.get(reverse("organization-list"))

    growth = len(many) - len(few)
    assert growth <= 2, f"{growth} extra queries for 10 extra jurisdictions ({len(few)} -> {len(many)})"
