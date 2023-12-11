from django import forms
from django.core.exceptions import ValidationError
from django.forms import DateField
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout

from vitrina.datasets.models import Dataset
from vitrina.fields import FilerFileField
from vitrina.helpers import inline_fields
from vitrina.resources.models import DatasetDistribution, Format
from vitrina.structure.models import Metadata


class DatasetResourceForm(forms.ModelForm):
    name = forms.CharField(label=_('Kodinis pavadinimas'), required=False)
    access = forms.ChoiceField(label=_("Prieigos lygmuo"), choices=Metadata.ACCESS_TYPES, required=False)
    period_start = DateField(
        widget=forms.TextInput(attrs={'type': 'date'}),
        required=False,
        label=_("Periodo pradžia"),
        help_text=_(
            "Data nuo kada duomenys yra aktualūs."
        ),
    )
    period_end = DateField(
        widget=forms.TextInput(attrs={'type': 'date'}),
        required=False,
        label=_("Periodo pabaiga"),
        help_text=_(
            "Data nuo kada duomenys nebėra aktualūs."
        ),
    )
    access_url = forms.URLField(
        # TODO: Bulma does not support type: 'url'
        widget=forms.TextInput(),
        label=_("Prieigos nuoroda"),
        help_text=_(
            "Nuoroda į svetainę, kurioje galima rasti tiesiogines duomenų "
            "atsisiuntimo nuorodas."
        ),
        required=False,
    )
    download_url = forms.URLField(
        # TODO: Bulma does not support type: 'url'
        widget=forms.TextInput(),
        label=_("Atsisiuntimo nuoroda"),
        help_text=_(
            "Tiesioginė duomenų atsisiuntimo nuoroda. Ši nuoroda turi rodyti "
            "tiesiogiai į CSV, JSON ar kito formato duomenų failą."
        ),
        required=False,
    )
    file = FilerFileField(
        upload_to=DatasetDistribution.UPLOAD_TO,
        label=_('Duomenų failas'),
        help_text=_(
            'Atvirų duomenų katalogas nėra skirtas duomenų talpinimui ir '
            'įprastinių atveju duomenys turėtu būti talpinami atvirų duomenų '
            'Saugykloje ar kitoje vietoje, pateikiant tiesioginę duomenų '
            'atsisiuntimo nuorodą. Tačiau nedidelės apimties (iki 5Mb) '
            'duomenų failus, galima talpinti ir kataloge.'
        ),
        required=False
    )
    data_service = forms.ModelChoiceField(
        label=_("Duomenų paslauga"),
        required=False,
        queryset=Dataset.public.all()
    )

    class Meta:
        model = DatasetDistribution
        fields = (
            'title',
            'description',
            'geo_location',
            'period_start',
            'period_end',
            'access_url',
            'format',
            'data_service',
            'download_url',
            'file',
            'name',
            'access',
            'is_parameterized',
            'upload_to_storage'
            'imported',
        )

    def __init__(self, dataset, *args, **kwargs):
        self.dataset = dataset
        super().__init__(*args, **kwargs)
        resource = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if resource else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs['novalidate'] = ''
        self.helper.form_id = "resource-form"
        self.helper.layout = Layout(
            Field('title', placeholder=_("Šaltinio pavadinimas"), css_class="control is-expanded"),
            Field('description', placeholder=_("Detalus šaltinio aprašas"), rows="2"),
            Field('name'),
            Field('access'),
            Field('is_parameterized'),
            Field('upload_to_storage'),
            Field('geo_location', placeholder=_("Pateikitę geografinę padėtį")),
            inline_fields(
                Field('period_start', placeholder=_("Pasirinkite pradžios datą")),
                Field('period_end', placeholder=_("Pasirinkite pabaigos datą")),
            ),
            Field('access_url'),
            Field('format'),
            Field('download_url'),
            Field('imported'),
            Field('data_service'),
            Field('file', placeholder=_("Šaltinio failas")),
            Submit('submit', button, css_class='button is-primary'),
        )

        related_datasets = self.dataset.related_datasets.values_list('dataset__pk', flat=True)
        self.fields['data_service'].queryset = self.fields['data_service'].queryset.filter(pk__in=related_datasets)

        if resource and resource.metadata.first():
            self.initial['access'] = resource.metadata.first().access
            self.initial['name'] = resource.metadata.first().name

        if not dataset.type.filter(name='catalog'):
            self.fields['imported'].widget = forms.HiddenInput()

    def clean(self):
        file = self.cleaned_data.get('file')
        url = self.cleaned_data.get('download_url')
        if file and url:
            raise ValidationError(_(
                "Užpildykit vieną iš pasirinktų laukų: URL lauką arba "
                "įkelkit failą, ne abu."
            ))
        if not file and not url:
            self.add_error('download_url', _(
                "Pateikite duomenų atsisiuntimo nuorodą."
            ))
            self.add_error('file', _(
                "Arba įkelkite duomenų faią."
            ))
        return self.cleaned_data

    def clean_access(self):
        access = self.cleaned_data.get('access')
        if access == '':
            return None
        return access


class FormatAdminForm(forms.ModelForm):
    extension = forms.CharField(label=_("Failo plėtinys"))
    title = forms.CharField(label=_("Pavadinimas"))
    mimetype = forms.CharField(label=_("MIME tipas"))

    class Meta:
        model = Format
        fields = ('extension', 'title', 'mimetype', 'rating',)
