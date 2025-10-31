from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from vitrina.users.models import User

PROXY_TYPE_CHOICES = [
    ("generic", "Generic"),
    ("service", "Service"),
    ("external", "External"),
    ("legal", "Legal"),
]


class FakeViispForm(forms.Form):
    email = forms.EmailField(label=_("El. paštas"), required=True)
    lt_company_code = forms.IntegerField(
        label=_("Įmonės kodas"),
        help_text=_("Įveskite Lietuvoje registruotos įmonės kodą."),
        required=False,
        min_value=1,
    )
    proxy_type = forms.ChoiceField(label=_("JA atstovavimo tipas"), choices=PROXY_TYPE_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "fake-viisp-form"
        self.helper.layout = Layout(
            Field("email"),
            Field("lt_company_code"),
            Field("proxy_type"),
            Submit("submit", _("Prisijungti"), css_class="button is-primary"),
        )

    def clean_email(self) -> str:
        email = self.cleaned_data.get("email")
        if not User.objects.filter(email=email).exists():
            raise ValidationError(_("Naudotojas su tokiu el. paštu neegzistuoja."))
        return email
