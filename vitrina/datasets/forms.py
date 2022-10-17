from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Submit, Layout
from parler.forms import TranslatableModelForm, TranslatedField
from parler.views import TranslatableModelFormMixin

from .models import Dataset
from django.utils.translation import gettext_lazy as _
from django.forms import TextInput, CharField
from django.forms import DateField
from haystack.forms import FacetedSearchForm
from ..classifiers.models import Licence, Frequency


class NewDatasetForm(TranslatableModelForm, TranslatableModelFormMixin):
    title = TranslatedField(form_class=CharField, label=_('Pavadinimas'), required=True)
    description = TranslatedField(label=_('Aprašymas'), widget=TextInput())

    class Meta:
        model = Dataset
        fields = (
            'is_public',
            'tags',
            'category',
            'licence',
            'frequency',
            'access_rights',
            'distribution_conditions',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "dataset-form"
        self.helper.layout = Layout(
            Div(Div(Field('is_public', css_class='checkbox', placeholder=_('Ar duomenys vieši'),),
                    css_class='control'), css_class='field'),
            Div(Div(Field('title', css_class='input', placeholder=_('Duomenų rinkinio pavadinimas')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('description', css_class='input', placeholder=_('Detalus duomenų rinkinio aprašas')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('tags', css_class='input', placeholder=_('Surašykite aktualius raktinius žodžius')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('category', css_class='input'),
                    css_class='control'), css_class='field'),
            Div(Div(Field('licence', css_class='input'),
                    css_class='control'), css_class='field'),
            Div(Div(Field('frequency', css_class='input'),
                    css_class='control'), css_class='field'),
            Div(Div(Field('access_rights', css_class='input', placeholder=_('Pateikite visas prieigos teises kurios aktualios šiam duomenų rinkiniui')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('distribution_conditions', css_class='input', placeholder=_('Pateikite visas salygas kurios reikalingos norint platinti duomenų rinkinį')),
                    css_class='control'), css_class='field'),
            Submit('submit', _('Patvirtinti'), css_class='button is-primary'),
        )

        instance = self.instance if self.instance and self.instance.pk else None
        if not instance:
            if Licence.objects.filter(is_default=True).exists():
                default_licence = Licence.objects.filter(is_default=True).first()
                self.initial['licence'] = default_licence
            if Frequency.objects.filter(is_default=True).exists():
                default_frequency = Frequency.objects.filter(is_default=True).first()
                self.initial['frequency'] = default_frequency


class DatasetSearchForm(FacetedSearchForm):
    date_from = DateField(required=False)
    date_to = DateField(required=False)

    def search(self):
        sqs = super().search()

        if not self.is_valid():
            return self.no_query_found()
        if self.cleaned_data.get('date_from'):
            sqs = sqs.filter(published__gte=self.cleaned_data['date_from'])
        if self.cleaned_data.get('date_to'):
            sqs = sqs.filter(published__lte=self.cleaned_data['date_to'])
        return sqs

    def no_query_found(self):
        return self.searchqueryset.all()
