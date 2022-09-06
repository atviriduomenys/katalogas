from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Submit, Layout
from django import forms
from .models import Dataset
from django.utils.translation import gettext_lazy as _
from django.forms import Form, CharField, DateTimeField, IntegerField
from vitrina.fields import MultipleValueField, MultipleIntField


class NewDatasetForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ('is_public', 'title', 'description', 'tags',
                  'category', 'licence', 'update_frequency',
                  'access_rights', 'distribution_conditions', 'manager',
                  'representative_id')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div(Field('is_public', css_class='input', placeholder=_('Ar duomenys vieši')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('title', css_class='input', placeholder=_('Duomenų rinkinio pavadinimas')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('description', css_class='input', placeholder=_('Duomenų rinkinio aprašas')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('tags', css_class='input', placeholder=_('Duomenų rinkinio raktiniai žodžiai')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('category', css_class='input', placeholder=_('Duomenų rinkinio kategorija')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('licence', css_class='input', placeholder=_('Licencija')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('update_frequency', css_class='input', placeholder=_('Duomenų atnaujinimo periodiškumas')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('access_rights', css_class='input', placeholder=_('Prieigos teisės')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('distribution_conditions', css_class='input', placeholder=_('Platinimo salygos')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('manager', css_class='input', placeholder=_('Rinkinio tvarkytojas')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('representative_id', css_class='input', placeholder=_('Rinkinio tvarkytojas')),
                    css_class='control'), css_class='field'),
            Submit('submit', _('Patvirtinti'), css_class='button is-primary'),
        )


class DatasetFilterForm(Form):
    q = CharField(required=False)
    date_from = DateTimeField(required=False)
    date_to = DateTimeField(required=False)
    status = CharField(required=False)
    tags = MultipleValueField(required=False)
    category = MultipleIntField(required=False)
    organization = IntegerField(required=False)
    frequency = IntegerField(required=False)
