from typing import Optional, List, Any
from urllib.parse import urlencode

from django.core.handlers.wsgi import WSGIRequest
from django.utils.translation import gettext_lazy as _

from crispy_forms.layout import Div
from crispy_forms.layout import Submit


def get_selected_value(
    request: WSGIRequest,
    title: str,
    multiple: bool = False,
    is_int: bool = True,
) -> Optional[List[Any]]:
    selected_value = [] if multiple else None
    value = request.GET.getlist(title) if multiple else request.GET.get(title)
    if value:
        selected_value = value
        if is_int:
            try:
                if multiple:
                    selected_value = list(map(int, value))
                else:
                    selected_value = int(value)
            except ValueError:
                return [] if multiple else None
    return selected_value


def get_filter_url(
    request: WSGIRequest,
    key: str,
    value: str,
    append: bool = False,
) -> str:
    query_dict = dict(request.GET.copy())
    if append and key in query_dict:
        query_dict[key].append(value)
    else:
        query_dict[key] = [value]
    return "?" + urlencode(query_dict, True)


def buttons(*args):
    return Div(
        Div(*args),
        css_class="field is-grouped is-grouped-centered",
    )


def submit(title=None):
    title = title or _("Patvirtinti")
    return Submit('submit', title, css_class='button is-primary'),
