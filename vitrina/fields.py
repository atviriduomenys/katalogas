from django.core.exceptions import ValidationError
from django.forms import TextInput, Field


class MultipleValueWidget(TextInput):
    def value_from_datadict(self, data, files, name):
        return data.getlist(name)


class MultipleValueField(Field):
    widget = MultipleValueWidget


def clean_int(x):
    try:
        return int(x)
    except ValueError:
        raise ValidationError("Cannot convert to integer: {}".format(repr(x)))


class MultipleIntField(MultipleValueField):
    def clean(self, value):
        return [clean_int(x) for x in value]
