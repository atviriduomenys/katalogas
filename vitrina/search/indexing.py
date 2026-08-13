import logging

from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.template.loader import render_to_string

from vitrina.datasets.models import Dataset
from vitrina.requests.models import Request
from vitrina.resources.models import DatasetDistribution
from vitrina.search.models import (
    DatasetSearchDoc,
    DatasetSearchFacet,
    RequestSearchDoc,
    RequestSearchFacet,
)
from vitrina.structure.models import Model, Property

logger = logging.getLogger(__name__)


def _dataset_categories(dataset):
    categories = []
    for category in dataset.category.all():
        categories.extend([cat.pk for cat in category.get_ancestors() if cat.dataset_set.exists()])
        categories.append(category.pk)
    return categories


DATASET_FACETS = {
    "status": lambda dataset: [dataset.status],
    "organization": lambda dataset: [dataset.organization_id],
    "creator": lambda dataset: dataset.get_creators(),
    "jurisdiction": lambda dataset: [dataset.jurisdiction()],
    "category": _dataset_categories,
    "parent_category": lambda dataset: dataset.parent_category(),
    "groups": lambda dataset: dataset.get_group_list(),
    "frequency": lambda dataset: [dataset.frequency_id],
    "tags": lambda dataset: dataset.get_tag_list(),
    "formats": lambda dataset: dataset.filter_formats(),
    "level": lambda dataset: [dataset.get_level()],
    "type": lambda dataset: dataset.public_types(),
    "access_rights": lambda dataset: [dataset.access_rights],
    "subclass": lambda dataset: [dataset.subclass.name if dataset.subclass_id else None],
}


def _request_categories(request):
    categories = []
    if request.dataset_id and request.dataset.category:
        for category in request.dataset.category.all():
            categories = [cat.pk for cat in category.get_ancestors() if cat.dataset_set.exists()]
            categories.append(category.pk)
    return categories


UNASSIGNED_ORGANIZATION = -1


def _request_organizations(request):
    organizations = [
        organization_id
        for organization_id in request.requestassignment_set.values_list("organization__pk", flat=True)
        if organization_id is not None
    ]
    return organizations or [UNASSIGNED_ORGANIZATION]


def _request_jurisdictions(request):
    return [
        assignment.organization.jurisdiction_id
        for assignment in request.requestassignment_set.select_related("organization")
        if assignment.organization and assignment.organization.jurisdiction_id
    ]


REQUEST_FACETS = {
    "status": lambda request: [request.status],
    "dataset_status": lambda request: request.dataset_statuses(),
    "organization": _request_organizations,
    "jurisdiction": _request_jurisdictions,
    "category": _request_categories,
    "parent_category": lambda request: request.dataset_parent_categories(),
    "groups": lambda request: request.dataset_group_list(),
    "tags": lambda request: request.dataset_get_tag_list(),
}


def indexable_datasets():
    translation_model = Dataset._parler_meta.root_model
    return Dataset.objects.filter(
        deleted__isnull=True,
        deleted_on__isnull=True,
        organization_id__isnull=False,
    ).filter(Exists(translation_model.objects.filter(master_id=OuterRef("pk"), title__isnull=False)))


def dataset_index_queryset():
    return (
        indexable_datasets()
        .select_related("organization", "organization__jurisdiction", "frequency", "subclass")
        .prefetch_related(
            "tags",
            "translations",
            "subclass__translations",
            "category",
            "category__datasetgroupcategoryuri_set",
            "excluded_groups",
            "type",
            "part_of",
            "related_datasets",
            "metadata",
            "project_set",
            Prefetch(
                "datasetdistribution_set",
                queryset=DatasetDistribution.objects.select_related("format").prefetch_related("translations"),
            ),
            Prefetch(
                "model_set",
                queryset=Model.objects.prefetch_related(
                    "metadata",
                    Prefetch("model_properties", queryset=Property.objects.prefetch_related("metadata")),
                ),
            ),
            Prefetch("dataset_request", queryset=Request.objects.prefetch_related("translations")),
        )
    )


def indexable_requests():
    return Request.public.filter().distinct()


def request_index_queryset():
    return indexable_requests().prefetch_related(
        "translations",
        "requestassignment_set__organization",
        "dataset__category__datasetgroupcategoryuri_set",
        "dataset__excluded_groups",
        "dataset__tags",
    )


def _facet_rows(obj, facets):
    for field, get_values in facets.items():
        for value in get_values(obj) or ():
            if value is None or value == "":
                continue
            yield field, str(value)


def _render_text(obj, template):
    return render_to_string(template, {"object": obj})


@transaction.atomic
def _write_dataset(dataset):
    DatasetSearchDoc.objects.update_or_create(
        dataset_id=dataset.pk,
        defaults={
            "text": _render_text(dataset, "search/indexes/vitrina_datasets/dataset_text.txt"),
            "title_lt": dataset.safe_translation_getter("title", language_code="lt", any_language=False) or "",
            "title_en": dataset.safe_translation_getter("title", language_code="en", any_language=False) or "",
            "published_or_created": dataset.published_created_sort(),
            "type_order": dataset.type_order(),
        },
    )

    rows = {(field, value) for field, value in _facet_rows(dataset, DATASET_FACETS)}
    DatasetSearchFacet.objects.filter(dataset_id=dataset.pk).delete()
    DatasetSearchFacet.objects.bulk_create(
        [DatasetSearchFacet(dataset_id=dataset.pk, field=field, value=value) for field, value in sorted(rows)]
    )


@transaction.atomic
def _write_request(request):
    RequestSearchDoc.objects.update_or_create(
        request_id=request.pk,
        defaults={
            "text": _render_text(request, "search/indexes/vitrina_requests/request_text.txt"),
            "title_lt": request.safe_translation_getter("title", language_code="lt", any_language=False) or "",
            "title_en": request.safe_translation_getter("title", language_code="en", any_language=False) or "",
        },
    )

    rows = {(field, value) for field, value in _facet_rows(request, REQUEST_FACETS)}
    RequestSearchFacet.objects.filter(request_id=request.pk).delete()
    RequestSearchFacet.objects.bulk_create(
        [RequestSearchFacet(request_id=request.pk, field=field, value=value) for field, value in sorted(rows)]
    )


@transaction.atomic
def _remove_dataset(pk):
    DatasetSearchDoc.objects.filter(pk=pk).delete()
    DatasetSearchFacet.objects.filter(dataset_id=pk).delete()


@transaction.atomic
def _remove_request(pk):
    RequestSearchDoc.objects.filter(pk=pk).delete()
    RequestSearchFacet.objects.filter(request_id=pk).delete()


def index_dataset(dataset):
    if indexable_datasets().filter(pk=dataset.pk).exists():
        _write_dataset(dataset)
    else:
        _remove_dataset(dataset.pk)


def index_request(request):
    if indexable_requests().filter(pk=request.pk).exists():
        _write_request(request)
    else:
        _remove_request(request.pk)


CHUNK_SIZE = 200


def _in_chunks(queryset, pks):
    for start in range(0, len(pks), CHUNK_SIZE):
        yield from queryset.filter(pk__in=pks[start : start + CHUNK_SIZE])


def rebuild(stdout=None):
    dataset_pks = list(indexable_datasets().values_list("pk", flat=True))
    datasets = 0
    for dataset in _in_chunks(dataset_index_queryset(), dataset_pks):
        _write_dataset(dataset)
        datasets += 1

    keep_datasets = indexable_datasets().values("pk")
    DatasetSearchDoc.objects.exclude(dataset_id__in=keep_datasets).delete()
    DatasetSearchFacet.objects.exclude(dataset_id__in=keep_datasets).delete()

    request_pks = list(indexable_requests().values_list("pk", flat=True))
    requests = 0
    for request in _in_chunks(request_index_queryset(), request_pks):
        _write_request(request)
        requests += 1

    keep_requests = indexable_requests().values("pk")
    RequestSearchDoc.objects.exclude(request_id__in=keep_requests).delete()
    RequestSearchFacet.objects.exclude(request_id__in=keep_requests).delete()

    if stdout:
        stdout.write(f"Indexed {datasets} datasets and {requests} requests.")
    return datasets, requests
