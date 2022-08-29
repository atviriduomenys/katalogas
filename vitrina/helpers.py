from typing import Optional, List, Any
from urllib.parse import urlencode

from django.core.handlers.wsgi import WSGIRequest


def get_selected_value(request: WSGIRequest, title: str, multiple: bool = False, is_int: bool = True) \
        -> Optional[List[Any]]:
    selected_value = [] if multiple else None
    value = request.GET.getlist(title) if multiple else request.GET.get(title)
    if value:
        selected_value = value
        if is_int:
            try:
                selected_value = [int(val) for val in value] if multiple else int(value)
            except ValueError:
                return [] if multiple else None
    return selected_value


def get_filter_url(request: WSGIRequest, key: str, value: str, append: bool = False) -> str:
    query_dict = dict(request.GET.copy())
    if append and key in query_dict:
        query_dict[key].append(value)
    else:
        query_dict[key] = [value]
    return "?" + urlencode(query_dict, True)
