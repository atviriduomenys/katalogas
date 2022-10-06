from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout
from django import forms
from .models import Dataset
from django.utils.translation import gettext_lazy as _
from django.forms import Form, CharField, DateTimeField, IntegerField
from vitrina.fields import MultipleValueField, MultipleIntField


class DatasetForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = (
            'is_public',
            'title',
            'description',
            'tags',
            'category',
            'licence',
            'frequency',
            'access_rights',
            'distribution_conditions',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if project_instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.form_id = "dataset-form"
        self.helper.layout = Layout(
            Field('is_public',
                  placeholder=_('Ar duomenys vieši')),
            Field('title',
                  placeholder=_('Duomenų rinkinio pavadinimas')),
            Field('description',
                  placeholder=_('Detalus duomenų rinkinio aprašas')),
            Field('tags',
                  placeholder=_('Surašykite aktualius raktinius žodžius')),
            Field('category'),
            Field('licence'),
            Field('frequency'),
            Field('access_rights',
                  placeholder=_('Pateikite visas prieigos teises kurios aktualios šiam duomenų rinkiniui')),
            Field('distribution_conditions',
                  placeholder=_('Pateikite visas salygas kurios reikalingos norint platinti duomenų rinkinį')),
            Submit('submit', button, css_class='button is-primary')
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
    
