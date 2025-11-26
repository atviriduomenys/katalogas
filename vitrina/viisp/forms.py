from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import AuthenticationForm


PROXY_TYPE_CHOICES = [
    ("generic", "Generic"),
    ("service", "Service"),
    ("external", "External"),
    ("legal", "Legal"),
]


class FakeViispForm(AuthenticationForm):
    lt_company_code = forms.CharField(
        label=_("Įmonės kodas"),
        help_text=_("Įveskite Lietuvoje registruotos įmonės kodą."),
        required=False,
    )
    proxy_type = forms.ChoiceField(label=_("JA atstovavimo tipas"), choices=PROXY_TYPE_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "fake-viisp-form"
        self.helper.layout = Layout(
            Field("username"),
            Field("password"),
            Field("lt_company_code"),
            Field("proxy_type"),
            Submit("submit", _("Prisijungti"), css_class="button is-primary"),
        )
