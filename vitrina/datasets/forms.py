from parler.forms import TranslatableModelForm, TranslatedField
from parler.views import TranslatableModelFormMixin
from django import forms
from django.forms import TextInput, CharField, DateField, ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout
from haystack.forms import FacetedSearchForm

from vitrina.classifiers.models import Frequency, Licence
from vitrina.orgs.forms import RepresentativeCreateForm, RepresentativeUpdateForm

from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.projects.models import Project


class DatasetForm(TranslatableModelForm, TranslatableModelFormMixin):
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


class AddProjectForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['projects']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "dataset-add-project-form"
        if self.user.is_superuser or self.user.is_staff:
            self.fields['projects'].queryset = Project.objects.filter()
        else:
            self.fields['projects'].queryset = Project.objects.filter(user=self.user)
        self.helper.layout = Layout(
            Field('projects'),
            Submit('submit', _("Pridėti"), css_class='button is-primary')
        )

    projects = ModelMultipleChoiceField(
        label=_('Projektai'),
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )


class DatasetMemberUpdateForm(RepresentativeUpdateForm):
    object_model = Dataset


class DatasetMemberCreateForm(RepresentativeCreateForm):
    object_model = Dataset
