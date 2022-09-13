from django.forms import Form, CharField, DateTimeField, IntegerField

from vitrina.fields import MultipleValueField, MultipleIntField


class DatasetFilterForm(Form):
    q = CharField(required=False)
    date_from = DateTimeField(required=False)
    date_to = DateTimeField(required=False)
    status = CharField(required=False)
    tags = MultipleValueField(required=False)
    category = MultipleIntField(required=False)
    organization = IntegerField(required=False)
    frequency = IntegerField(required=False)
