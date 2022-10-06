from django import forms
from django.core.exceptions import ValidationError
from django.forms import DateField
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout

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
        label=_("Prieigos prie duomenų nuoroda"),
        help_text=_(
            "Nuoroda į svetainę, kurioje galima rasti tiesiogines duomenų "
            "atsisiuntimo nuorodas."
        ),
        required=False,
    )
    download_url = forms.URLField(
        # TODO: Bulma does not support type: 'url'
        widget=forms.TextInput(),
        label=_("Atsisniuntimo nuoroda"),
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
            'access_url',
            'format',
            'download_url',
            'file',
            'region',
            'municipality',
            'period_start',
            'period_end',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "resource-form"
        self.helper.layout = Layout(
            Field('title', placeholder=_("Šaltinio pavadinimas")),
            Field('description', placeholder=_("Detalus šaltinio aprašas")),
            Field('access_url'),
            Field('format'),
            Field('download_url'),
            Field('file', placeholder=_("Šaltinio failas")),
            Field('region'),
            Field('municipality'),
            Field('period_start', placeholder=_("Pasirinkite pradžios datą")),
            Field('period_end', placeholder=_("Pasirinkite pabaigos datą")),
            Submit('submit', _("Patvirtinti"), css_class='button is-primary'),
        )

    def clean(self):
        filename = self.cleaned_data.get('filename')
        url = self.cleaned_data.get('url')
        if filename and url:
            raise ValidationError(_(
                "Užpildykit vieną iš pasirinktų laukų: URL lauką arba "
                "įkelkit failą, ne abu"
            ))
        if not filename and not url:
            raise ValidationError(_("Užpildykit URL lauką arba įkelkit failą"))
        return self.cleaned_data
