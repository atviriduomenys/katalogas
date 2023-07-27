from typing import List, Any, Dict, Type

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import HttpRequest

from django.db.models import Q

from vitrina.helpers import get_filter_url
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
