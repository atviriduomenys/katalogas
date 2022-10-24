from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout
from django import forms
from .models import Dataset, DatasetStructure
from django.utils.translation import gettext_lazy as _
from django.forms import DateField
from haystack.forms import FacetedSearchForm
from ..classifiers.models import Licence, Frequency


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


class DatasetStructureImportForm(forms.ModelForm):
    file = forms.FileField(label=_("Failas"), required=True)

    class Meta:
        model = DatasetStructure
        fields = ('file',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "dataset-structure-form"
        self.helper.layout = Layout(
            Field('file'),
            Submit('submit', _('Patvirtinti'), css_class='button is-primary'),
        )
