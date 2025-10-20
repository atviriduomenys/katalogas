from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.forms import ModelForm, CharField, Textarea, ModelChoiceField, BooleanField
from django.contrib.contenttypes.models import ContentType
from django.db.models import QuerySet

from vitrina.fields import FilerImageField
from vitrina.projects.models import Project, UseCaseClientScope, UseCaseClient
from vitrina.orgs.models import Organization

from django.utils.translation import gettext_lazy as _

from vitrina.smart_contracts.models import AgreementScope


class ProjectForm(ModelForm):
    title = CharField(label=_("Pavadinimas"), help_text=_("Siūlomo panaudojimo atvejo pavadinimas."))
    description = CharField(
        label=_("Aprašymas"),
        widget=Textarea,
        help_text=_("Išsamus pasiūlymo aprašymas."),
    )
    organization = ModelChoiceField(
        Organization.objects.none(),
        label=_("Organizacija"),
        required=False,
        help_text=_(
            "Nurodžius organizaciją panaudos atvejis kuriamas organizacijos vardu, nenurodžius - privataus asmens vardu. Atitinka odrl:asignee"
        ),
    )
    url = CharField(
        label=_("Nuoroda į panaudojimo atvejį"),
        required=False,
        help_text=_("Nuoroda susijusi su siūlomu panaudojimo atveju (github, pagrindinė svetainė, kt.)."),
    )
    image = FilerImageField(
        label=_("Paveiksliukas"),
        required=False,
        upload_to=Project.UPLOAD_TO,
        help_text=_("Paveiksliukas susijęs su pasiūlytu panaudojimo atveju."),
    )
    is_public = BooleanField(
        label=_("Panaudos atvejis matomas viešai"),
        required=False,
        help_text=_(
            "Pažymėkite, jeigu norite, kad panaudos atvejis būtų matomas viešai visiems. Kitu atveju bus matomas tik gavėjo ir teikėjų organizacijoms."
        ),
    )

    class Meta:
        model = Project
        fields = ["title", "description", "organization", "url", "image", "is_public"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        organization_id = kwargs.pop("organization_id", None)
        super().__init__(*args, **kwargs)
        project_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if project_instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "project-form"
        self.fields["organization"].queryset = self._organization_queryset()
        if not project_instance and organization_id:
            self.fields["organization"].initial = organization_id
        if project_instance and project_instance.user != self.user:
            self.fields["organization"].empty_label = None
        self.helper.layout = Layout(
            Field("title", placeholder=_("Pavadinimas")),
            Field("description", placeholder=_("Aprašymas")),
            Field("organization"),
            Field("url", placeholder=_("Nuoroda į panaudojimo atvejį")),
            Field("image"),
            Field("is_public"),
            Submit("submit", button, css_class="button is-primary"),
        )

    def _organization_queryset(self) -> QuerySet["Organization"]:
        if self.user.is_superuser or self.user.is_staff:
            return Organization.public.all()

        return Organization.public.filter(
            representatives__content_type=ContentType.objects.get_for_model(Organization),
            representatives__user=self.user,
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

    def __init__(self, *args, available_scopes: UseCaseClientScope = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["scope"].queryset = available_scopes
        self.fields["scope"].label_from_instance = lambda obj: str(obj.scope)
        button = _("Pridėti")
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "client-scope-form"
        self.helper.layout = Layout(
            Field("scope", placeholder=_("Leidimai")),
            Submit("submit", button, css_class="button is-primary"),
        )
