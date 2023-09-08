from typing import List, Any, Dict, Type

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import HttpRequest

from django.db.models import Q, Sum
from django.db.models.functions import ExtractQuarter, ExtractWeek

from vitrina.datasets.models import Dataset
from vitrina.helpers import get_filter_url
from vitrina.orgs.models import Representative
from vitrina.projects.models import Project
from vitrina.requests.models import Request, RequestObject


def update_facet_data(
    request: HttpRequest,
    facet_fields: List[str],
    field_name: str,
    model_class: Type = None,
    choices: Dict = None,
) -> List[Any]:
    updated_facet_data = []
    if facet_fields and field_name in facet_fields:
        for facet in facet_fields[field_name]:
            display_value = facet[0]
            if model_class:
                try:
                    obj = model_class.objects.get(pk=facet[0])
                    display_value = obj.title
                except ObjectDoesNotExist:
                    continue
            elif choices:
                display_value = choices.get(facet[0])
            data = {
                'filter_value': facet[0],
                'display_value': display_value,
                'count': facet[1],
                'url': get_filter_url(request, field_name, facet[0]),
            }
            updated_facet_data.append(data)
    return updated_facet_data


def get_projects(user, dataset, check_existence=False, order_value=None, form_query=False):
    if form_query:
        if user.is_staff:
            projects = Project.public.all()
        else:
            projects = Project.public.filter(user=user)

        projects = projects.exclude(Q(status=Project.REJECTED) | Q(datasets__pk__in=[dataset.pk]))
    else:
        projects = Project.public.filter(datasets=dataset).exclude(status=Project.REJECTED)

    if order_value:
        projects.order_by(order_value)

    if check_existence:
        return projects.exists()
    else:
        return projects


def get_requests(user, dataset):
    if user.is_staff:
        requests = Request.public.all()
    else:
        requests = Request.public.filter(user=user)

    dataset_req_ids = RequestObject.objects.filter(content_type=ContentType.objects.get_for_model(dataset),
                                                   object_id=dataset.pk).values_list('request_id', flat=True)
    requests = requests.exclude(Q(status=Request.REJECTED) | Q(pk__in=dataset_req_ids))
    return requests


def get_count_by_frequency(
    frequency,
    label,
    queryset,
    field,
    aggregate_field=None,
    group_field=None,
    only_latest=False,
):
    if frequency == 'Y':
        query = {
            f"{field}__year": label.year
        }
    elif frequency == 'Q':
        queryset = queryset.annotate(
            quarter=ExtractQuarter('created')
        )
        query = {
            f"{field}__year": label.year,
            "quarter": label.quarter
        }
    elif frequency == 'M':
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month
        }
    elif frequency == 'W':
        queryset = queryset.annotate(
            week=ExtractWeek('created')
        )
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month,
            "week": label.week
        }
    else:
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month,
            f"{field}__day": label.day
        }

    if aggregate_field:
        if only_latest and group_field:
            queryset_ids = queryset.order_by(
                group_field, f"-{field}"
            ).distinct(
                group_field
            ).values_list('pk', flat=True)
            queryset = queryset.filter(pk__in=queryset_ids)

            return queryset.filter(**query).aggregate(
                Sum(aggregate_field)
            )[f"{aggregate_field}__sum"] or 0
        else:
            return queryset.filter(**query).aggregate(
                Sum(aggregate_field)
            )[f"{aggregate_field}__sum"] or 0
    else:
        return queryset.filter(**query).count()


def get_frequency_and_format(duration):
    if duration == 'duration-yearly':
        frequency = 'Y'
        ff = 'Y'
    elif duration == 'duration-quarterly':
        frequency = 'Q'
        ff = 'Y M'
    elif duration == 'duration-monthly':
        frequency = 'M'
        ff = 'Y m'
    elif duration == 'duration-weekly':
        frequency = 'W'
        ff = 'Y W'
    else:
        frequency = 'D'
        ff = 'Y m d'
    return frequency, ff


def get_datasets_for_user(user):
    not_deleted_datasets = Dataset.objects.all().filter(deleted__isnull=True,
                                                        deleted_on__isnull=True,
                                                        organization_id__isnull=False,)
    coordinator_orgs = [rep.object_id for rep in
                        user.representative_set.filter(role=Representative.COORDINATOR)]
    public_datasets = not_deleted_datasets.filter(is_public=True)
    managed_datasets = not_deleted_datasets.filter(organization__in=coordinator_orgs)
    dataset_ids = [dataset.id for dataset in public_datasets] +\
                  [dataset.id for dataset in managed_datasets]
    return dataset_ids
