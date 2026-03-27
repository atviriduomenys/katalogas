from typing import Optional

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string

from vitrina.datasets.models import Dataset, Relation, DatasetRelation, DatasetGroup
from vitrina.datasets.services import DynamicResourceService
from vitrina.resources.models import DatasetDistribution as Distribution
from vitrina.resources.models import Format
from vitrina.resources.models import FormatName
from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Frequency
from vitrina.classifiers.models import Licence
from vitrina.orgs.models import Organization


DCAT_AP_RDF_TEMPLATE_NAME = "vitrina/api/edp/dcat_ap_rdf.html"


def get_datasets_for_rdf(qs):
    datasets = (
        qs.select_related("organization")
        .prefetch_related("category")
        .prefetch_related("translations")
        .prefetch_related("datasetdistribution_set")
        .prefetch_related("datasetdistribution_set__format")
        .order_by("published")
    )
    for dataset in datasets:
        distributions = []
        if not dataset.service:
            distributions = [
                distribution
                for dist in dataset.datasetdistribution_set.all()
                if (distribution := _get_distribution(dataset, dist)) is not None
            ]

            if dataset.is_part_of_dataservice():
                dataset_resources = DynamicResourceService(dataset, None)
                dynamic_distributions = dataset_resources.generate_resources(is_for_rdf_export=True)
                distributions.extend(dynamic_distributions)

        yield {
            "uri": dataset.get_absolute_url(),
            "translations": (
                {
                    "lang": t.language_code,
                    "title": t.title,
                    "description": t.description,
                }
                for t in dataset.translations.order_by("language_code")
            ),
            "categories": _get_categories(dataset),
            "hvd_categories": [
                _get_hvd_category(c)
                for c in dataset.category.filter(datasetgroupcategoryuri__group__name=DatasetGroup.HVD)
            ]
            if dataset.is_hvd
            else [],
            "keywords": [k.name for k in dataset.tags.all()],
            "published": dataset.published,
            "modified": dataset.modified,
            "organization": dataset.organization,
            "creators": Organization.objects.filter(pk__in=dataset.get_creators()),
            "frequency": _get_frequency(dataset.frequency),
            "distributions": distributions,
            "contact": _get_contact_email(dataset),
            "landing_page": dataset.landing_page,
            "service": dataset.service,
            "endpoint_url": dataset.endpoint_url,
            "endpoint_type": _get_format(dataset.endpoint_type),
            "endpoint_description": dataset.endpoint_description,
            "endpoint_description_type": dataset.endpoint_description_type,
            "related_datasets": (
                _get_rel_dataset(relation)
                for relation in dataset.related_datasets.filter(relation__name=Relation.SERVICE)
            ),
            "access_rights": dataset.access_rights,
            "subclass": dataset.subclass,
            "is_hvd": dataset.is_hvd,
        }


def _encode_xml_control_chars(content: str) -> str:
    return content.replace("\t", "&#x9;")


def render_rdf_response(request: HttpRequest, datasets: QuerySet[Dataset]) -> HttpResponse:
    content = render_to_string(
        DCAT_AP_RDF_TEMPLATE_NAME,
        {"datasets": get_datasets_for_rdf(datasets)},
        request=request,
    )
    content = _encode_xml_control_chars(content)
    return HttpResponse(content, content_type="application/rdf+xml")


def _get_distribution(dataset: Dataset, dist: Distribution):
    dist_type = None
    if dist.format:
        if dist.format.extension in (FormatName.API, FormatName.UAPI):
            if dataset.model_set.all():
                return None
            dist_type = "WEB_SERVICE"
        else:
            dist_type = "DOWNLOADABLE_FILE"
        dist_type = "http://publications.europa.eu/" + "resource/authority/distribution-type/" + dist_type

    return {
        "uri": dist.get_absolute_url(),
        "type": dist_type,
        "translations": [
            {
                "lang": "lt",
                "title": dist.title,
                "description": dist.description,
            },
        ],
        "download_url": dist.get_download_url(),
        "access_url": dist.get_access_url(),
        "access_service": dist.data_service.get_absolute_url() if dist.data_service else None,
        "licence": _get_licence(dist.licence),
        "conditions": dist.conditions or "",
        "format": _get_format(dist.format),
        "compression_format": _get_format(dist.compression_format),
        "packaging_format": _get_format(dist.packaging_format),
        "media_type": _get_media_type(dist.format),
        "created": dist.created,
        "modified": dist.modified,
        "is_hvd": dist.is_hvd,
    }


def _get_categories(dataset):
    categories = []

    for c in dataset.category.all():
        root_category = c.get_root()
        if root_category not in categories:
            categories.append(root_category)

    return [_get_category(c) for c in categories]


def _get_category(category: Category):
    return {
        "uri": category.uri,
        "translations": [
            {
                "lang": "lt",
                "title": category.title,
            },
        ],
    }


def _get_hvd_category(category: Category):
    uri = ""
    if group_category_uri := category.datasetgroupcategoryuri_set.filter(group__name=DatasetGroup.HVD).first():
        uri = group_category_uri.uri
    return {
        "uri": uri,
        "translations": [
            {
                "lang": "lt",
                "title": category.title,
            },
        ],
    }


def _get_rel_dataset(relation: DatasetRelation):
    return {
        "uri": relation.dataset.get_absolute_url(),
    }


def _get_frequency(frequency: Optional[Frequency]):
    if not frequency:
        return

    return {
        "uri": frequency.uri,
        "translations": [
            {
                "lang": "lt",
                "title": frequency.title,
            },
            {
                "lang": "en",
                "title": frequency.title_en,
            },
        ],
    }


def _get_licence(licence: Optional[Licence]):
    if licence and licence.url:
        return {"uri": licence.url}


def _get_format(format: Optional[Format]):
    if format and format.uri:
        return {
            "uri": format.uri,
        }


def _get_media_type(format: Optional[Format]):
    if format and format.media_type_uri:
        return {
            "uri": format.media_type_uri,
        }


def _get_contact_email(dataset: Dataset) -> str:
    if dataset.contact and (email := dataset.contact.get_email()):
        return email

    if dataset.publisher and (email := dataset.publisher.email):
        return email

    if dataset.organization and (email := dataset.organization.email):
        return email

    return ""
