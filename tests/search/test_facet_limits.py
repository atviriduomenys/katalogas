import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.search.queries import TAGS_FACET_LIMIT

TAG_COUNT = TAGS_FACET_LIMIT + 20


@pytest.mark.django_db
def test_tags_facet_stops_at_its_limit(app: DjangoTestApp):
    for index in range(TAG_COUNT):
        DatasetFactory(
            organization=OrganizationFactory(title=f"Org {index:03d}"),
            tags=[f"tag{index:03d}"],
        )

    response = app.get(reverse("dataset-list"))

    assert len(response.context["facets"]["fields"]["tags"]) == TAGS_FACET_LIMIT


@pytest.mark.django_db
def test_facet_keeps_the_most_common_values(app: DjangoTestApp):
    common = "common"
    for index in range(TAGS_FACET_LIMIT + 5):
        tags = [f"tag{index:03d}"]
        if index < 3:
            tags.append(common)
        DatasetFactory(organization=OrganizationFactory(title=f"Org {index:03d}"), tags=tags)

    response = app.get(reverse("dataset-list"))
    tags_facet = response.context["facets"]["fields"]["tags"]

    assert len(tags_facet) == TAGS_FACET_LIMIT
    assert tags_facet[0][1] == 3, "The most common tag must come first"
