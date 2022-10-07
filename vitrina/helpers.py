from typing import Optional, List, Any
from urllib.parse import urlencode

from django.contrib.sites.models import Site
from django.core.handlers.wsgi import WSGIRequest
from haystack.forms import FacetedSearchForm


def get_selected_value(form: FacetedSearchForm, field_name: str, multiple: bool = False, is_int: bool = True) \
        -> Optional[List[Any]]:
    selected_value = [] if multiple else None
    for selected_facet in form.selected_facets:
        if selected_facet.split(":")[0] == "%s_exact" % field_name:
            if multiple:
                selected_value.append(selected_facet.split(":")[1])
            else:
                selected_value = selected_facet.split(":")[1]
                break
    if selected_value and is_int:
        try:
            selected_value = [int(val) for val in selected_value] if multiple else int(selected_value)
        except ValueError:
            return [] if multiple else None
    return selected_value


def get_filter_url(request: WSGIRequest, key: str, value: str) -> str:
    query_dict = dict(request.GET.copy())
    if "selected_facets" in query_dict:
        query_dict["selected_facets"].append('%s_exact:%s' % (key, value))
    else:
        query_dict["selected_facets"] = "%s_exact:%s" % (key, value)
    return "?" + urlencode(query_dict, True)


def get_current_domain(request: WSGIRequest) -> str:
    protocol = "https" if request.is_secure() else "http"
    domain = Site.objects.get_current().domain
    return request.build_absolute_uri("%s://%s" % (protocol, domain))
