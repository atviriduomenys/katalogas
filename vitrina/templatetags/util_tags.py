import numbers
from datetime import date
from typing import Iterable

import requests
from django import template
from django.contrib.contenttypes.models import ContentType
from extra_settings.models import Setting
register = template.Library()
assignment_tag = getattr(register, 'assignment_tag', register.simple_tag)


@assignment_tag
def get_value_by_key(dictionary, key):
    return dictionary.get(key)


@register.filter()
def is_number(value):
    return isinstance(value, numbers.Number)


@register.filter()
def is_dict(value):
    return isinstance(value, dict)


@register.filter
def get_list(dictionary, key):
    return dictionary.getlist(key)


@register.filter(name='range')
def range_(value: int) -> Iterable[int]:
    return range(value)


@assignment_tag
def define(val=None):
    return val


@assignment_tag
def get_content_type(obj):
    return ContentType.objects.get_for_model(obj)


@register.filter()
def is_past_due(value):
    return date.today() > value


@assignment_tag
def get_google_analytics_id():
    google_analytics_id = Setting.objects.filter(name="GOOGLE_ANALYTICS_ID").first()
    if google_analytics_id:
        if google_analytics_id.value != '':
            return google_analytics_id.value
        else:
            return None
    else:
        return None


@assignment_tag
def logged_in_user(_user, _logged_in_user):
    if _logged_in_user != '':
        return _logged_in_user
    else:
        return _user
