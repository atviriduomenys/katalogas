from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit
from django.forms import ModelForm, CharField, Textarea, ModelChoiceField, BooleanField, RadioSelect, HiddenInput

from vitrina.fields import FilerImageField
from vitrina.projects.models import Project, UseCaseClientScope, UseCaseClient
from vitrina.orgs.models import Organization
from vitrina.users.models import User

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
        label=_("Panaudos atvejo iniciatorius"),
        widget=RadioSelect,
        required=False,
        help_text=_(
            "Nurodytos organizacijos vardu, bus galimybė sudaryti duomenų gavimo sutartis, sutartyje nurodant panaudojimo atvejį, kaip duomenų gavimo tikslą.(Atitinka odrl:assignee). Pasirinkus fizinį asmenį, sudaryti sutarčių galimybės nėra. Fizinis asmuo nurodomas tik kaip panaudojimo atvejo autorius."
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
        self.user: User = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        project_instance = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if project_instance else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "project-form"
        self.fields["organization"].empty_label = f"{_('Fizinis asmuo')} ({self.user})"
        if project_instance:
            self.fields.pop("organization", None)
        elif (organization := self.user.viisp_organization) and self.user.is_representative_of(organization, True):
            self.fields["organization"].queryset = Organization.objects.filter(pk=organization.pk)
            self.fields["organization"].label_from_instance = lambda org: _("Organizacija") + f" ({org})"
            self.fields["organization"].initial = organization

        self.helper.layout = Layout(
            Field("is_public"),
            Field("title", placeholder=_("Pavadinimas")),
            Field("description", placeholder=_("Aprašymas")),
            Field("organization"),
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
