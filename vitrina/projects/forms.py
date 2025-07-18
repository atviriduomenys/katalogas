from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.forms import ModelForm, CharField, Textarea, ModelChoiceField

from vitrina.fields import FilerImageField
from vitrina.projects.models import Project, UseCaseClientScope, UseCaseClient

from django.utils.translation import gettext_lazy as _

from vitrina.smart_contracts.models import AgreementScope


class ProjectForm(ModelForm):
    title = CharField(label=_("Pavadinimas"), help_text=_("Siūlomo panaudojimo atvejo pavadinimas."))
    description = CharField(
        label=_("Aprašymas"),
        widget=Textarea,
        help_text=_("Išsamus pasiūlymo aprašymas."),
    )
    url = CharField(
        label=_("Nuoroda į panaudojimo atvejį"),
        required=False,
        help_text=_("Nuoroda susijusi su siūlomu panaudojimo atveju (github, pagrindinė svetainė, kt.).")
    )
    image = FilerImageField(
        label=_("Paveiksliukas"),
        required=False,
        upload_to=Project.UPLOAD_TO,
        help_text=_("Paveiksliukas susijęs su pasiūlytu panaudojimo atveju.")
    )

    class Meta:
        model = Project
        fields = ["title", "description", "url", "image"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if project_instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "project-form"
        self.helper.layout = Layout(
            Field("title", placeholder=_("Pavadinimas")),
            Field("description", placeholder=_("Aprašymas")),
            Field("url", placeholder=_("Nuoroda į panaudojimo atvejį")),
            Field("image"),
            Submit("submit", button, css_class="button is-primary"),
        )

class ClientCreateForm(ModelForm):
    name = CharField(label=_("Pavadinimas"), help_text=_("Kliento pavadinimas"))

    class Meta:
        model = UseCaseClient
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        project_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if project_instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "client-form"
        self.helper.layout = Layout(
            Field("name", placeholder=_("Pavadinimas")),
            Submit("submit", button, css_class="button is-primary"),
        )


class ClientScopeCreateForm(ModelForm):
    scope = ModelChoiceField(
        queryset=AgreementScope.objects.none(),
        label=_("Leidimas"),
        help_text=_("Pasirinkite leidimą"),
    )

    class Meta:
        model = UseCaseClientScope
        fields = ["scope"]

    def __init__(self, *args, available_scopes=None, use_case_client=None, **kwargs):
        super().__init__(*args, **kwargs)
        if available_scopes is not None and use_case_client is not None:
            existing_pairs = set(
                UseCaseClientScope.objects.filter(use_case_client=use_case_client)
                .values_list("resource", "action")
            )
            filtered_scopes = [
                scope for scope in available_scopes
                if (scope.resource, scope.action) not in existing_pairs
            ]
            self.fields["scope"].queryset = AgreementScope.objects.filter(
                pk__in=[s.pk for s in filtered_scopes]
            )

            self.fields["scope"].label_from_instance = lambda obj: str(obj.resource) + "_" + str(obj.action)
        if not self.fields["scope"].queryset.exists():
            self.fields["scope"].required = False
        button = _("Pridėti")
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "client-scope-form"
        self.helper.layout = Layout(
            Field("scope", placeholder=_("Leidimai")),
            Submit("submit", button, css_class="button is-primary"),
        )
