from typing import Optional, List, Any
from urllib.parse import urlencode

from django.contrib.sites.models import Site
from django.core.handlers.wsgi import WSGIRequest

from vitrina.users.models import User


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


def get_current_domain(request: WSGIRequest) -> str:
    protocol = "https" if request.is_secure() else "http"
    domain = Site.objects.get_current().domain
    return request.build_absolute_uri("%s://%s" % (protocol, domain))


def can_manage_history(obj: Any, user: User) -> bool:
    if user.is_authenticated:
        if user.is_staff:
            return True
        if hasattr(obj, "organization") and obj.organization and obj.organization == user.organization:
            return True
        if hasattr(obj, "user") and obj.user and obj.user == user:
            return True
    return False
