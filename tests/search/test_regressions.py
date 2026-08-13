from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.classifiers.factories import CategoryFactory
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request, RequestAssignment, RequestObject
from vitrina.search.indexing import UNASSIGNED_ORGANIZATION
from vitrina.search.models import DatasetSearchDoc, DatasetSearchFacet, RequestSearchFacet


def _published(year):
    return datetime(year, 1, 15, 12, 0, tzinfo=datetime_timezone.utc)


@pytest.mark.django_db
def test_tags_set_after_the_first_save_reach_the_index():
    dataset = DatasetFactory(organization=OrganizationFactory(title="Org One"))
    dataset.tags.set(["alpha", "beta"])
    dataset.save()

    values = set(DatasetSearchFacet.objects.filter(dataset=dataset, field="tags").values_list("value", flat=True))
    tag_pks = {str(tag.pk) for tag in dataset.tags.all()}

    assert values == tag_pks
    assert len(values) == 2


@pytest.mark.django_db
def test_an_indexing_error_does_not_undo_the_save():
    with patch("vitrina.search.signals._reindex_dataset", side_effect=ValueError("boom")):
        dataset = DatasetFactory(organization=OrganizationFactory(title="Org Two"))

    assert Dataset.objects.filter(pk=dataset.pk).exists()


@pytest.mark.django_db
def test_a_request_assigned_to_no_organization_saves_and_indexes():
    request = RequestFactory()
    RequestAssignment.objects.create(request=request, organization=None, status=Request.CREATED)
    request.save()

    assert Request.objects.filter(pk=request.pk).exists()


@pytest.mark.django_db
def test_a_request_with_no_assignment_keeps_the_unassigned_buckets(app: DjangoTestApp):
    request = RequestFactory()

    values = dict(
        RequestSearchFacet.objects.filter(request=request, field="organization").values_list("field", "value")
    )

    assert values["organization"] == str(UNASSIGNED_ORGANIZATION)

    response = app.get(reverse("request-list"), {"selected_facets": f"organization_exact:{UNASSIGNED_ORGANIZATION}"})
    assert [item.pk for item in response.context["object_list"]] == [request.pk]


@pytest.mark.django_db
def test_search_matches_words_that_are_not_next_to_each_other(app: DjangoTestApp):
    organization = OrganizationFactory(title="Statistikos departamentas")
    DatasetFactory(
        organization=organization,
        title={"lt": "Gyventoju surasymas", "en": "Population census"},
        description={"lt": "Aprasymas", "en": "Description"},
        tags=["demografija"],
    )
    DatasetFactory(organization=OrganizationFactory(title="Kita organizacija"), tags=["kita"])

    response = app.get(reverse("dataset-list"), {"q": "surasymas Statistikos"})
    assert len(response.context["object_list"]) == 1

    response = app.get(reverse("dataset-list"), {"q": "demografija surasymas"})
    assert len(response.context["object_list"]) == 1

    response = app.get(reverse("dataset-list"), {"q": "surasymas nerastas"})
    assert len(response.context["object_list"]) == 0


@pytest.mark.django_db
def test_paging_never_repeats_or_drops_a_dataset(app: DjangoTestApp):
    for index in range(45):
        DatasetFactory(organization=OrganizationFactory(title=f"Org {index:03d}"))

    seen = []
    for page in (1, 2, 3):
        response = app.get(reverse("dataset-list"), {"sort": "sort-by-relevance", "page": page})
        seen.extend(item.pk for item in response.context["object_list"])

    assert len(seen) == len(set(seen)), "A dataset showed on more than one page"
    assert len(seen) == Dataset.objects.filter(search_doc__isnull=False).count()


@pytest.mark.django_db
def test_request_category_facet_drops_all_but_one_category_of_its_dataset():
    dataset = DatasetFactory(organization=OrganizationFactory(title="Org Three"))
    dataset.category.add(CategoryFactory(title="First category"))
    dataset.category.add(CategoryFactory(title="Second category"))
    dataset.save()

    request = RequestFactory(dataset=dataset)
    RequestObject.objects.create(
        request=request,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=dataset.pk,
    )
    request.save()

    values = RequestSearchFacet.objects.filter(request=request, field="category").values_list("value", flat=True)

    assert dataset.category.count() == 2
    assert len(values) == 1


@pytest.mark.django_db
def test_each_word_of_a_query_is_measured_on_its_own(app: DjangoTestApp):
    DatasetFactory(
        organization=OrganizationFactory(title="Org Zeta"),
        title={"lt": "Kirmele", "en": "Worm"},
        description={"lt": "Aprasas", "en": "Description"},
    )

    def found(query):
        return len(app.get(reverse("dataset-list"), {"q": query}).context["object_list"])

    assert found("Kirmele") == 1
    assert found("rm") == 0
    assert found("Kirmele rm") == 0


@pytest.mark.django_db
def test_a_stats_page_counts_only_the_datasets_that_pass_the_filter(app: DjangoTestApp):
    wanted = OrganizationFactory(title="Wanted org")
    other = OrganizationFactory(title="Other org")
    DatasetFactory(organization=wanted, published=_published(2021))
    for _ in range(3):
        DatasetFactory(organization=other, published=_published(2021))

    response = app.get(
        reverse("dataset-stats-published"),
        {"selected_facets": f"organization_exact:{wanted.pk}"},
    )

    assert len(response.context["object_list"]) == 1
    assert sum(response.context["year_stats"].values()) == 1


@pytest.mark.django_db
def test_the_date_facet_reports_a_month_before_the_catalogue_start(app: DjangoTestApp):
    DatasetFactory(organization=OrganizationFactory(title="Old org"), published=_published(2016))

    response = app.get(reverse("dataset-list"))
    buckets = dict(response.context["facets"]["dates"]["published"])

    assert buckets[date(2016, 1, 1)] == 1


@pytest.mark.django_db
def test_a_raw_save_still_builds_the_search_row():
    dataset = DatasetFactory(organization=OrganizationFactory(title="Raw org"))
    DatasetSearchDoc.objects.filter(pk=dataset.pk).delete()

    dataset.save_base(raw=True)

    assert DatasetSearchDoc.objects.filter(pk=dataset.pk).exists()


@pytest.mark.django_db
def test_a_dataset_with_no_date_sorts_last(app: DjangoTestApp):
    organization = OrganizationFactory(title="Dated org")
    DatasetFactory(organization=organization, published=_published(2021))
    undated = DatasetFactory(organization=organization, published=_published(2022))
    Dataset.objects.filter(pk=undated.pk).update(created=None, published=None)
    undated.refresh_from_db()
    undated.save()

    response = app.get(reverse("dataset-list"), {"sort": "sort-by-date-newest"})

    assert [item.pk for item in response.context["object_list"]][-1] == undated.pk
