import csv
from typing import List, Any, Dict, Type

from django.core.exceptions import ObjectDoesNotExist
from django.core.handlers.wsgi import WSGIRequest

from vitrina.helpers import get_filter_url


def update_facet_data(request: WSGIRequest, facet_fields: List[str],
                      field_name: str, model_class: Type = None, choices: Dict = None) -> List[Any]:
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


STANDARDIZED_HEADER_FIELDS = [
    'id',
    'dataset',
    'resource',
    'base',
    'model',
    'property',
    'type',
    'ref',
    'source',
    'prepare',
    'level',
    'access',
    'uri',
    'title',
    'description'
]


def is_standardized(file) -> bool:
    try:
        reader = csv.reader(open(file.path, encoding='utf-8'), delimiter=",")
        header = next(reader)
    except BaseException:
        return False
    if header == STANDARDIZED_HEADER_FIELDS:
        return True
    return False
