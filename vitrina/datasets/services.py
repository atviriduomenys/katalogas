from collections import OrderedDict
from typing import List, Any, Dict, Type

import numpy as np
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import HttpRequest

from django.db.models import Q
from haystack.backends import SQ

from vitrina.datasets.models import Dataset
from vitrina.helpers import get_filter_url
from vitrina.messages.helpers import email
from vitrina.messages.models import Subscription
from vitrina.orgs.helpers import is_org_dataset_list
from vitrina.orgs.models import Organization
from vitrina.orgs.services import has_perm, Action
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
                    user_orgs.append(rep.content_object.organization.pk)
            requests = Request.public.filter(Q(user=user) | Q(organizations__pk__in=user_orgs))
        else:
            requests = Request.public.filter(user=user)

    dataset_req_ids = RequestObject.objects.filter(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk
    ).values_list('request_id', flat=True)
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
                    user_orgs.append(rep.content_object.organization.pk)
            return request.organizations.filter(pk__in=user_orgs).exists()
    return False


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
    elif duration == 'duration-daily':
        frequency = 'D'
        ff = 'Y m d'
    else:
        frequency = 'Y'
        ff = 'Y'
    return frequency, ff


def get_values_for_frequency(frequency, field):
    if frequency == 'Y':
        values = [f"{field}__year"]
    elif frequency == 'Q':
        values = [f"{field}__year", f"{field}__quarter"]
    elif frequency == 'M':
        values = [f"{field}__year", f"{field}__month"]
    elif frequency == 'W':
        values = [f"{field}__year", f"{field}__month", f"{field}__week"]
    else:
        values = [f"{field}__year", f"{field}__month", f"{field}__day"]
    return values


def get_query_for_frequency(frequency, field, label):
    if frequency == 'Y':
        query = {
            f"{field}__year": label.year
        }
    elif frequency == 'Q':
        query = {
            f"{field}__year": label.year,
            f"{field}__quarter": label.quarter
        }
    elif frequency == 'M':
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month
        }
    elif frequency == 'W':
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month,
            f"{field}__week": label.week
        }
    else:
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month,
            f"{field}__day": label.day
        }
    return query


def sort_publication_stats(sorting, values, keys, stats, sorted_value_index):
    if sorting == 'sort-year-desc':
        stats = OrderedDict(sorted(stats.items(), reverse=True))
    elif sorting == 'sort-year-asc':
        stats = OrderedDict(sorted(stats.items(), reverse=False))
    elif sorting == 'sort-desc':
        stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
    elif sorting == 'sort-asc':
        stats = {keys[i]: values[i] for i in sorted_value_index}
    return stats


def sort_publication_stats_reversed(sorting, values, keys, stats, sorted_value_index):
    if sorting == 'sort-year-desc':
        stats = OrderedDict(sorted(stats.items(), reverse=False))
    elif sorting == 'sort-year-asc':
        stats = OrderedDict(sorted(stats.items(), reverse=True))
    elif sorting == 'sort-asc':
        stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
    elif sorting == 'sort-desc':
        stats = {keys[i]: values[i] for i in sorted_value_index}
    return stats


def get_total_by_indicator_from_stats(st, indicator, total):
    if indicator == 'request-count':
        if st.request_count is not None:
            total += st.request_count
        return total
    elif indicator == 'project-count':
        if st.project_count is not None:
            total += st.project_count
        return total
    elif indicator == 'distribution-count':
        if st.distribution_count is not None:
            total += st.distribution_count
        return total
    elif indicator == 'object-count':
        if st.object_count is not None:
            total += st.object_count
        return total
    elif indicator == 'field-count':
        if st.field_count is not None:
            total += st.field_count
        return total
    elif indicator == 'model-count':
        if st.model_count is not None:
            total += st.model_count
        return total
    elif indicator == 'level-average':
        lev = []
        if st.maturity_level is not None:
            lev.append(st.maturity_level)
        level_avg = 0
        if lev:
            level_avg = int(sum(lev) / len(lev))
        return level_avg


def get_public_dataset_id_list():
    public_datasets = Dataset.objects.filter(is_public=True)
    public_dataset_id_list = [dataset.id for dataset in public_datasets]
    return public_dataset_id_list


def filter_datasets_for_user(user, datasets):
    coordinator_orgs = [rep.object_id for rep in
                        user.representative_set.filter(content_type=ContentType.objects.get_for_model(Organization))]
    public_dataset_id_list = get_public_dataset_id_list()
    coordinated_datasets = Dataset.objects.filter(organization_id__in=coordinator_orgs)
    dataset_id_list = public_dataset_id_list + [dataset.id for dataset in coordinated_datasets]
    datasets = datasets.filter(django_id__in=dataset_id_list)
    return datasets


def get_datasets_for_user(request, datasets):
    is_org_dataset = False
    if is_org_dataset_list(request) and request.user.is_authenticated:
        if request.user.organization_id == request.resolver_match.kwargs['pk']:
            is_org_dataset = True
    datasets = filter_out_non_public_datasets_for_user(request.user, datasets, is_org_dataset)
    datasets = datasets.models(Dataset)
    return datasets


def filter_out_non_public_datasets_for_user(user, datasets, is_org_dataset):
    if user.is_authenticated:
        if not (user.is_staff or user.is_superuser):
            if user.representative_set:
                if is_org_dataset:
                    return datasets.filter(SQ(is_public='true') | SQ(is_public='false') | SQ(managers__contains=user.id))
                else:
                    return datasets.filter(SQ(is_public='true') | SQ(managers__contains=user.id))
            else:
                return datasets.filter(is_public='true')
        else:
            return datasets
    else:
        return datasets.filter(is_public='true')


def create_subscription(user, dataset):
    return Subscription.objects.create(
        user=user,
        content_type=ContentType.objects.get_for_model(Dataset),
        object_id=dataset.pk,
        sub_type=Subscription.DATASET,
        email_subscribed=True,
        dataset_comments_sub=True
    )


def manage_subscriptions_for_representative(subscribe, user, dataset):
    subscription = Subscription.objects.filter(user=user,
                                               object_id=dataset.id,
                                               content_type=get_content_type_for_model(Dataset))
    if subscribe:
        if not subscription:
            create_subscription(user, dataset)
            email(user.email, 'vitrina/messages/emails/subscribed', {
                'obj': dataset,
            })
        else:
            subscription.update(
                dataset_comments_sub=True,
                request_comments_sub=True,
                project_comments_sub=True,
            )
            email(user.email, 'vitrina/messages/emails/subscription_updated', {
                'obj': dataset,
            })
    else:
        if subscription:
            subscription.delete()
