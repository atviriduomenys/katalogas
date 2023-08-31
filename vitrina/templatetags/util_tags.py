import numbers
from datetime import date
from typing import Iterable

from django import template
from django.contrib.contenttypes.models import ContentType

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
