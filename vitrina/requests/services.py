from typing import List, Any, Dict, Type

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import HttpRequest

from vitrina.helpers import get_filter_url
from vitrina.orgs.models import Representative, Organization
from vitrina.orgs.services import has_perm, Action


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
                    display_value = "Nepriskirta"
            elif choices:
                display_value = choices.get(facet[0])
            elif facet[0] == "UNASSIGNED":
                display_value = "Nepriskirta"
            data = {
                'filter_value': facet[0],
                'display_value': display_value,
                'count': facet[1],
                'url': get_filter_url(request, field_name, facet[0]),
            }
            updated_facet_data.append(data)
    return updated_facet_data


def can_update_request_org(request, user):
    if not user.is_authenticated:
        return False

    is_my_request = user == request.user
    is_supervisor = Representative.objects.filter(user=user, role=Representative.SUPERVISOR).exists()

    if not (is_my_request or is_supervisor or user.is_superuser or user.is_staff):
        if user.organization and user.organization in request.organizations.all():
            return has_perm(user, Action.UPDATE, request)

        representatives = user.representative_set.filter(
            content_type=ContentType.objects.get_for_model(Organization),
            object_id__isnull=False,
            object_id__in=request.organizations.values_list('id', flat=True)
        )
        if not representatives.exists():
            return False

    return has_perm(user, Action.UPDATE, request)
