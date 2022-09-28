from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Div, Submit
from django import forms
from django.core.exceptions import ValidationError
from django.forms import DateField

from .models import DatasetDistribution
from django.utils.translation import gettext_lazy as _


class DatasetResourceForm(forms.ModelForm):
    period_start = DateField(widget=forms.TextInput(attrs={'type': 'date'}), required=False)
    period_end = DateField(widget=forms.TextInput(attrs={'type': 'date'}), required=False)

    class Meta:
        model = DatasetDistribution
        fields = (
            'title',
            'description',
            'period_start',
            'period_end',
            'filename',
            'url',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "resource-form"
        self.helper.layout = Layout(
            Div(Div(Field('title', css_class='input', placeholder=_('Šaltinio pavadinimas')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('description', css_class='input', placeholder=_('Detalus šaltinio aprašas')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('period_start', css_class='input', placeholder=_('Pasirinkite pradžios datą')),
                    css_class='control'), css_class='field'),
            Div(Div(Field('period_end', css_class='input', placeholder=_('Pasirinkite pabaigos datą')),
                    css_class='control'), css_class='field'),
            Submit('submit', _('Patvirtinti'), css_class='button is-primary'),
        )
        if not self.instance.filename:
            self.helper.layout.insert(-1, Div(Div(Field('url', css_class='input',
                                                        placeholder=_('Šaltinio nuoroda')),
                                              css_class='control'), css_class='field'),)
        if not self.instance.url:
            self.helper.layout.insert(-1, Div(Div(Field('filename', css_class='input',
                                                        placeholder=_('Šaltinio failas')),
                                              css_class='control'), css_class='field'),)

    def clean(self):
        filename = self.cleaned_data.get('filename')
        url = self.cleaned_data.get('url')
        if filename and url:
            raise ValidationError(_("Užpildykit vieną iš pasirinktų laukų: URL lauką arba įkelkit failą, ne abu"))
        if not filename and not url:
            raise ValidationError(_("Užpildykit URL lauką arba įkelkit failą"))
        return self.cleaned_data
