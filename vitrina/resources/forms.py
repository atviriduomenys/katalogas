from django import forms
from django.core.exceptions import ValidationError
from django.forms import DateField
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout

from vitrina.helpers import inline_fields
from vitrina.resources.models import DatasetDistribution


class DatasetResourceForm(forms.ModelForm):
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
            'download_url',
            'file',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        resource = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if resource else _("Sukurti")
        self.helper = FormHelper()
        self.helper.form_id = "resource-form"
        self.helper.layout = Layout(
            Field('title', placeholder=_("Šaltinio pavadinimas"), css_class="control is-expanded"),
            Field('description', placeholder=_("Detalus šaltinio aprašas"), rows="2"),
            Field('geo_location', placeholder=_("Pateikitę geografinę padėtį")),
            inline_fields(
                Field('period_start', placeholder=_("Pasirinkite pradžios datą")),
                Field('period_end', placeholder=_("Pasirinkite pabaigos datą")),
            ),
            Field('access_url'),
            Field('format'),
            Field('download_url'),
            Field('file', placeholder=_("Šaltinio failas")),
            Submit('submit', button, css_class='button is-primary'),
        )

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