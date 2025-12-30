from collections import OrderedDict
from typing import List, Any, Dict, Type

import numpy as np
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import HttpRequest

from django.db.models import Q
from django.urls import reverse
from haystack.backends import SQ
from haystack.query import SearchQuerySet

from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.helpers import get_filter_url
from vitrina.helpers import email
from vitrina.messages.models import Subscription
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.requests.models import Request, RequestObject
from vitrina.resources.models import Format
from vitrina.settings import SPINTA_SERVER_URL
from vitrina.structure.models import Version
from vitrina.users.models import User
from rest_framework.request import Request as DrfRequest


def update_facet_data(
    request: HttpRequest,
    facet_fields: List[str],
    field_name: str,
    model_class: Type = None,
    choices: Dict = None,
    use_str: bool = False,
) -> List[Any]:
    updated_facet_data = []
    if facet_fields and field_name in facet_fields:
        for facet in facet_fields[field_name]:
            display_value = facet[0]
            if model_class:
                try:
                    obj = model_class.objects.get(pk=facet[0])
                    if use_str:
                        display_value = str(obj)
                    else:
                        display_value = obj.title
                except ObjectDoesNotExist:
                    continue
            elif choices:
                display_value = choices.get(facet[0])
                if not display_value:
                    continue
            data = {
                "filter_value": facet[0],
                "display_value": display_value,
                "count": facet[1],
                "url": get_filter_url(request, field_name, facet[0]),
            }
            updated_facet_data.append(data)
    return updated_facet_data


def get_requests(user, dataset):
    if user.is_staff or user.is_superuser:
        requests = Request.public.all()
    else:
        if has_perm(user, Action.UPDATE, dataset):
            user_orgs = []
            if user.organization:
                user_orgs.append(user.organization.pk)
            for rep in user.representative_set.all():
                if isinstance(rep.content_object, Organization):
                    user_orgs.append(rep.content_object.pk)
                elif isinstance(rep.content_object, Dataset):
                    if rep.content_object.organization:
                        user_orgs.append(rep.content_object.organization.pk)
            requests = Request.public.filter(Q(user=user) | Q(organizations__pk__in=user_orgs))
        else:
            requests = Request.public.filter(user=user)

    dataset_req_ids = RequestObject.objects.filter(
        content_type=ContentType.objects.get_for_model(dataset), object_id=dataset.pk
    ).values_list("request_id", flat=True)
    requests = requests.exclude(Q(status=Request.REJECTED) | Q(pk__in=dataset_req_ids))
    return requests


def has_remove_from_request_perm(dataset, request, user):
    if user.is_authenticated:
        if user.is_staff or user.is_superuser or request.user == user:
            return True
        if has_perm(user, Action.UPDATE, dataset):
            user_orgs = []
            if user.organization:
                user_orgs.append(user.organization.pk)
            for rep in user.representative_set.all():
                if isinstance(rep.content_object, Organization):
                    user_orgs.append(rep.content_object.pk)
                elif isinstance(rep.content_object, Dataset):
                    if rep.content_object.organization:
                        user_orgs.append(rep.content_object.organization.pk)
            return request.organizations.filter(pk__in=user_orgs).exists()
    return False


def get_frequency_and_format(duration):
    if duration == "duration-yearly":
        frequency = "Y"
        ff = "Y"
    elif duration == "duration-quarterly":
        frequency = "Q"
        ff = "Y M"
    elif duration == "duration-monthly":
        frequency = "M"
        ff = "Y m"
    elif duration == "duration-weekly":
        frequency = "W"
        ff = "Y W"
    elif duration == "duration-daily":
        frequency = "D"
        ff = "Y m d"
    else:
        frequency = "Y"
        ff = "Y"
    return frequency, ff


def get_values_for_frequency(frequency, field):
    if frequency == "Y":
        values = [f"{field}__year"]
    elif frequency == "Q":
        values = [f"{field}__year", f"{field}__quarter"]
    elif frequency == "M":
        values = [f"{field}__year", f"{field}__month"]
    elif frequency == "W":
        values = [f"{field}__year", f"{field}__month", f"{field}__week"]
    else:
        values = [f"{field}__year", f"{field}__month", f"{field}__day"]
    return values


def get_query_for_frequency(frequency, field, label):
    if frequency == "Y":
        query = {f"{field}__year": label.year}
    elif frequency == "Q":
        query = {f"{field}__year": label.year, f"{field}__quarter": label.quarter}
    elif frequency == "M":
        query = {f"{field}__year": label.year, f"{field}__month": label.month}
    elif frequency == "W":
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month,
            f"{field}__week": label.week,
        }
    else:
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month,
            f"{field}__day": label.day,
        }
    return query


def sort_publication_stats(sorting, values, keys, stats, sorted_value_index):
    if sorting == "sort-year-desc":
        stats = OrderedDict(sorted(stats.items(), reverse=True))
    elif sorting == "sort-year-asc":
        stats = OrderedDict(sorted(stats.items(), reverse=False))
    elif sorting == "sort-desc":
        stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
    elif sorting == "sort-asc":
        stats = {keys[i]: values[i] for i in sorted_value_index}
    return stats


def sort_publication_stats_reversed(sorting, values, keys, stats, sorted_value_index):
    if sorting == "sort-year-desc":
        stats = OrderedDict(sorted(stats.items(), reverse=False))
    elif sorting == "sort-year-asc":
        stats = OrderedDict(sorted(stats.items(), reverse=True))
    elif sorting == "sort-asc":
        stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
    elif sorting == "sort-desc":
        stats = {keys[i]: values[i] for i in sorted_value_index}
    return stats


def get_total_by_indicator_from_stats(st, indicator, total):
    if indicator == "request-count":
        if st.request_count is not None:
            total += st.request_count
        return total
    elif indicator == "project-count":
        if st.project_count is not None:
            total += st.project_count
        return total
    elif indicator == "distribution-count":
        if st.distribution_count is not None:
            total += st.distribution_count
        return total
    elif indicator == "object-count":
        if st.object_count is not None:
            total += st.object_count
        return total
    elif indicator == "field-count":
        if st.field_count is not None:
            total += st.field_count
        return total
    elif indicator == "model-count":
        if st.model_count is not None:
            total += st.model_count
        return total
    elif indicator == "level-average":
        lev = []
        if st.maturity_level is not None:
            lev.append(st.maturity_level)
        level_avg = 0
        if lev:
            level_avg = int(sum(lev) / len(lev))
        return level_avg
    return total


def get_public_dataset_id_list():
    public_datasets = Dataset.objects.filter(is_public=True)
    public_dataset_id_list = [dataset.id for dataset in public_datasets]
    return public_dataset_id_list


def filter_datasets_for_user(user: User, datasets: SearchQuerySet) -> SearchQuerySet:
    coordinator_orgs = [
        rep.object_id
        for rep in user.representative_set.filter(content_type=ContentType.objects.get_for_model(Organization))
    ]
    public_dataset_id_list = get_public_dataset_id_list()
    coordinated_datasets = Dataset.objects.filter(organization_id__in=coordinator_orgs)
    dataset_id_list = public_dataset_id_list + [dataset.id for dataset in coordinated_datasets]
    datasets = datasets.filter(django_id__in=dataset_id_list)
    return datasets


def get_datasets_for_user(request: DrfRequest, datasets: SearchQuerySet) -> SearchQuerySet:
    datasets = filter_out_non_public_datasets_for_user(request.user, datasets)
    datasets = datasets.models(Dataset)
    return datasets


def filter_out_non_public_datasets_for_user(user: User, datasets: SearchQuerySet) -> SearchQuerySet:
    public_filter: SQ = SQ(is_public="true", access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED))
    combined_filter = public_filter | SQ(resource_managers__in=[user.pk])
    if not user.is_authenticated:
        return datasets.filter(public_filter)
    elif user.is_staff or user.is_superuser:
        return datasets

    if user.is_gov_organization_manager:
        combined_filter |= SQ(
            is_public="true", access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC)
        )
    info_system_orgs = Representative.objects.filter(
        user=user, content_type=ContentType.objects.get_for_model(Organization), information_system_representative=True
    ).values_list("object_id", flat=True)
    open_data_orgs = Representative.objects.filter(
        user=user, content_type=ContentType.objects.get_for_model(Organization), open_data_representative=True
    ).values_list("object_id", flat=True)
    if info_system_orgs.all():
        combined_filter |= SQ(
            organization_id__in=info_system_orgs,
            subclass_name=DCATResourceSubclass.INFORMATION_SYSTEM,
            is_public="true",
            access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL),
        )
        combined_filter |= SQ(
            organization_id__in=info_system_orgs,
            is_public="true",
            access_rights__in=(Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC),
        ) & ~SQ(subclass_name=DCATResourceSubclass.INFORMATION_SYSTEM)
    if open_data_orgs.exists():
        return datasets.filter(public_filter)

    return datasets.filter(combined_filter)


def create_subscription(user, dataset):
    return Subscription.objects.create(
        user=user,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=dataset.pk,
        sub_type=Subscription.DATASET,
        email_subscribed=True,
        dataset_comments_sub=True,
    )


def manage_subscriptions_for_representative(subscribe, user, dataset, link):
    subscription = Subscription.objects.filter(
        user=user,
        object_id=dataset.id,
        content_type=get_content_type_for_model(Dataset),
    )
    if subscribe:
        if not subscription:
            if user.email:
                create_subscription(user, dataset)
                email(
                    [user.email],
                    "newsletter-dataset-subscription-created-representative",
                    "vitrina/messages/emails/sub/dataset_sub_created.md",
                    {"obj": dataset, "link": link},
                )
        else:
            subscription.update(
                dataset_comments_sub=True,
                request_comments_sub=True,
                project_comments_sub=True,
            )
            email(
                [user.email],
                "newsletter-dataset-subscription-updated-representative",
                "vitrina/messages/emails/sub/dataset_sub_updated.md",
                {"obj": dataset, "link": link},
            )
    else:
        if subscription:
            subscription.delete()


class DynamicResourceService:
    JSON_FORMAT = "JSON"
    JSONL_FORMAT = "JSONL"
    CSV_FORMAT = "CSV"
    RDF_FORMAT = "RDF"

    def __init__(self, dataset: Dataset, metadata_version: Version):
        self.dataset: Dataset = dataset
        self.metadata_version: Version = metadata_version
        self.dataset_service = Dataset.objects.filter(service=True, endpoint_url=SPINTA_SERVER_URL).first()
        self.uapi_distribution = self.dataset.datasetdistribution_set.filter(
            format__extension="UAPI", metadata_version=self.metadata_version
        ).first()  # ?

    def generate_resources(self, is_for_rdf_export=False):
        if not self.dataset.is_part_of_dataservice():
            return []

        models = self.dataset.model_set.filter(metadata_version=self.metadata_version)
        if not models:
            return []

        return [
            self._create_distribution(models, self.JSON_FORMAT, is_for_rdf_export),
            self._create_distribution(models, self.JSONL_FORMAT, is_for_rdf_export),
            self._create_distribution(models, self.RDF_FORMAT, is_for_rdf_export),
            *self._create_csv_distributions(models, is_for_rdf_export),
        ]

    def _create_distribution(self, models, distribution_format, is_for_rdf_export):
        download_url, distribution_name = self._generate_download_url(models, distribution_format)
        if is_for_rdf_export:
            format_uri = Format.objects.filter(title=distribution_format).values_list("uri", flat=True).first()
            format_media_type = (
                Format.objects.filter(title=distribution_format).values_list("media_type_uri", flat=True).first()
            )
            return {
                "uri": reverse(
                    "dynamic-resource-detail",
                    args=[
                        self.dataset.pk,
                        self.metadata_version.pk,
                        self.uapi_distribution.pk,
                        distribution_name,
                        distribution_format.lower(),
                    ],
                ),
                "translations": [
                    {
                        "lang": "lt",
                        "title": self.uapi_distribution.title,
                        "description": self.uapi_distribution.description,
                    },
                ],
                "type": self.uapi_distribution.type,
                "download_url": download_url,
                "access_url": self._generate_access_url(models),
                "access_service": self.uapi_distribution.data_service.get_absolute_url()
                if self.uapi_distribution.data_service
                else None,
                "licence": {"uri": self.uapi_distribution.licence.url}
                if self.uapi_distribution.licence and self.uapi_distribution.licence.url
                else None,
                "conditions": self.uapi_distribution.conditions or "",
                "format": {"uri": format_uri},
                "media_type": {"uri": format_media_type},
                "created": self.uapi_distribution.created,
                "modified": self.uapi_distribution.modified,
                "is_hvd": self.uapi_distribution.is_hvd,
            }
        return {
            "title": distribution_name,
            "format": distribution_format,
            "download_url": download_url,
            "models": list(models),
            "created": self.uapi_distribution.created,
            "modified": self.uapi_distribution.modified,
            "period_start": self.uapi_distribution.period_start,
            "period_end": self.uapi_distribution.period_end,
            "geo_location": self.uapi_distribution.geo_location,
            "data_service_id": self.dataset_service.id if self.dataset_service else None,
            "resource_url": reverse(
                "dynamic-resource-detail",
                args=[
                    self.dataset.pk,
                    self.metadata_version.pk,
                    self.uapi_distribution.pk,
                    distribution_name,
                    distribution_format.lower(),
                ],
            ),
        }

    def _create_csv_distributions(self, models, is_for_rdf_export, no_models=False):
        if no_models:
            return [self._create_distribution([], self.CSV_FORMAT, is_for_rdf_export)]
        return [self._create_distribution([model], self.CSV_FORMAT, is_for_rdf_export) for model in models]

    def _generate_access_url(self, models):
        if self.uapi_distribution.access_url:
            return self.uapi_distribution.access_url
        if models:
            return f"{SPINTA_SERVER_URL}/{'/'.join(models[0].full_name.split('/')[:-1])}"
        return ""

    def _generate_download_url(self, models, distribution_format):
        if (
            distribution_format == self.JSON_FORMAT
            or distribution_format == self.JSONL_FORMAT
            or distribution_format == self.RDF_FORMAT
        ):
            base_url = f"{SPINTA_SERVER_URL}/{'/'.join(models[0].full_name.split('/')[:-1])}"
            download_url = f"{base_url}/:all/:format/{distribution_format.lower()}"
            distribution_name = (
                models[0].full_name.split("/")[-2] if len(models[0].full_name.split("/")) > 1 else models[0].name
            )
        else:
            download_url = f"{SPINTA_SERVER_URL}/{models[0].full_name}/:format/csv"
            distribution_name = models[0].name

        return download_url, distribution_name

    def retrieve_data(self, dataset_pk, metadata_version, resource_name, distribution_format):
        dataset = Dataset.objects.get(pk=dataset_pk)
        models = dataset.model_set.filter(metadata_version=metadata_version)

        if distribution_format in [self.JSON_FORMAT, self.JSONL_FORMAT, self.RDF_FORMAT]:
            full_name_parts = (
                models[0].full_name if "/" not in models[0].full_name else "/".join(models[0].full_name.split("/")[:-1])
            )
            base_url = f"{SPINTA_SERVER_URL}/{full_name_parts}"
            download_url = f"{base_url}/:all/:format/{distribution_format.lower()}"
            return {
                "title": resource_name,
                "dataset": dataset,
                "models": models,
                "get_download_url": download_url,
                "created": self.uapi_distribution.created if self.uapi_distribution else None,
                "modified": self.uapi_distribution.modified if self.uapi_distribution else None,
                "period_start": self.uapi_distribution.period_start if self.uapi_distribution else None,
                "period_end": self.uapi_distribution.period_end if self.uapi_distribution else None,
                "geo_location": self.uapi_distribution.geo_location if self.uapi_distribution else None,
            }

        model = next(model for model in models if model.name == resource_name)
        download_url = f"{SPINTA_SERVER_URL}/{model.full_name}/:format/{distribution_format.lower()}"
        return {
            "title": resource_name,
            "dataset": dataset,
            "models": [model],
            "get_download_url": download_url,
            "created": self.uapi_distribution.created if self.uapi_distribution else None,
            "modified": self.uapi_distribution.modified if self.uapi_distribution else None,
            "period_start": self.uapi_distribution.period_start if self.uapi_distribution else None,
            "period_end": self.uapi_distribution.period_end if self.uapi_distribution else None,
            "geo_location": self.uapi_distribution.geo_location if self.uapi_distribution else None,
        }
