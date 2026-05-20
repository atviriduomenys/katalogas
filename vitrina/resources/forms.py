from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout
from parler.forms import TranslatedField, TranslatableModelForm

from vitrina.classifiers.models import Licence, Concept
from vitrina.datasets.models import Dataset
from vitrina.fields import FilerFileField, StringListField
from vitrina.resources.models import DatasetDistribution, Format
from vitrina.structure import AccessType
from django.db.models import Case, When, IntegerField

CODE_ORDER = ["COMPLETED", "DEVELOP", "PLANNED", "DEPRECATED", "WITHDRAWN"]


def _get_level_title(title, description=None):
    if description:
        return mark_safe(f'{title}<br/><p class="help">{description}</p>')
    else:
        return title


LEVEL_CHOICES = (
    (None, _get_level_title(_("Nenurodyta"))),
    (
        0,
        _get_level_title(
            _("Nėra identifikatoriaus"),
            _("Duomenyse nėra tokio duomenų lauko, kuris unikaliai identifikuoja objektą."),
        ),
    ),
    (
        1,
        _get_level_title(
            _("Neunikalus identifikatorius"),
            _(
                "Duomenų laukas parinktas kaip identifikatorius nėra unikalus arba parinktas "
                "laukas nėra privalomas ir ne visi objektai gali turėti reikšmę."
            ),
        ),
    ),
    (
        2,
        _get_level_title(
            _("Nepatikimas identifikatorius"),
            _("Duomenų lauko, kuris yra parinktas kaip identifikatorius, reikšmės gali keistis."),
        ),
    ),
    (
        3,
        _get_level_title(
            _("Patikimas identifikatorius"),
            _(
                "Naudojamas patikimas lokalus identifikatorius, tačiau objektams nėra priskirtas "
                "globalus nekintantis identifikatorius."
            ),
        ),
    ),
    (
        4,
        _get_level_title(
            _("Globalus identifikatorius"),
            _("Objektams priskirtas globalus nekintantis identifikatorius."),
        ),
    ),
)


class DatasetResourceForm(TranslatableModelForm):
    title = TranslatedField(label=_("Pavadinimas"), required=False)
    description = TranslatedField(label=_("Aprašymas"), required=False)
    name = forms.CharField(label=_("Kodinis pavadinimas"), required=False)
    access = forms.ChoiceField(
        label=_("Prieigos lygmuo"), choices=[("", _("nepasirinkta"))] + list(AccessType.choices), required=False
    )
    access_url = forms.URLField(
        # TODO: Bulma does not support type: 'url'
        widget=forms.TextInput(),
        label=_("Prieigos nuoroda"),
        help_text=_("Nuoroda į svetainę, kurioje galima rasti tiesiogines duomenų atsisiuntimo nuorodas."),
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
        label=_("Duomenų failas"),
        help_text=_(
            "Atvirų duomenų katalogas nėra skirtas duomenų talpinimui ir "
            "įprastinių atveju duomenys turėtu būti talpinami atvirų duomenų "
            "Saugykloje ar kitoje vietoje, pateikiant tiesioginę duomenų "
            "atsisiuntimo nuorodą. Tačiau nedidelės apimties (iki 5Mb) "
            "duomenų failus, galima talpinti ir kataloge."
        ),
        required=False,
    )
    data_service = forms.ModelChoiceField(
        label=_("Duomenų paslauga"),
        required=False,
        queryset=Dataset.public.filter(service=True),
    )
    level = forms.ChoiceField(
        label=_("Brandos lygis"),
        required=False,
        widget=forms.RadioSelect,
        choices=LEVEL_CHOICES,
    )
    applicable_legislation = StringListField(
        label=_("Teisinis pagrindas"),
        help_text=_(
            "Teisės aktas, kurio pagrindu yra valdomas ir tvarkomas duomenų rinkinys.<br>"
            "Norint nurodyti konkrečią vietą teisės akto dokumente, po „#“ pateikite konkrečią nuorodą, "
            "pvz., „#17.2“.<br>"
            "Tais atvejais, kai yra keli dokumentai su priedais: „#priedas1/17.2“, „17.2/17.2.5“, "
            "kur „priedas1“ yra dokumento failo pavadinimas.<br>"
            "Atitinka eli:LegalResource."
        ),
        required=False,
        unique=True,
    )

    class Meta:
        model = DatasetDistribution
        fields = (
            "title",
            "description",
            "geo_location",
            "access_url",
            "format",
            "compression_format",
            "packaging_format",
            "data_service",
            "download_url",
            "file",
            "name",
            "access",
            "level",
            "is_parameterized",
            "upload_to_storage",
            "imported",
            "licence",
            "conditions",
            "rights_relation",
            "temporal_resolution",
            "spatial_resolution",
            "applicable_legislation",
            "status",
            "is_hvd",
        )

    def __init__(self, dataset, *args, **kwargs):
        self.dataset = dataset
        super().__init__(*args, **kwargs)
        self.resource = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if self.resource else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "resource-form"
        self.fields["status"].required = True
        self.fields["status"].empty_label = None
        self.fields["status"].queryset = (
            Concept.objects.filter(concept_schemas__uri=DatasetDistribution.DISTRIBUTION_STATUS_URI)
            .distinct()
            .order_by(
                Case(
                    *[When(code=code, then=pos) for pos, code in enumerate(CODE_ORDER)],
                    default=len(CODE_ORDER),
                    output_field=IntegerField(),
                )
            )
        )
        self.fields["status"].label_from_instance = lambda obj: obj.safe_translation_getter("label", any_language=True)

        self.helper.layout = Layout(
            Field(
                "title",
                placeholder=_("Pateikties pavadinimas"),
                css_class="control is-expanded",
            ),
            Field("description", placeholder=_("Detalus pateikties aprašas"), rows="2"),
            Field("name"),
            Field("temporal_resolution"),
            Field("spatial_resolution"),
            Field("access"),
            Field("level"),
            Field("is_parameterized"),
            Field("geo_location", placeholder=_("Pateikitę geografinę padėtį")),
            Field("access_url"),
            Field("format"),
            Field("compression_format"),
            Field("packaging_format"),
            Field("status"),
            Field("file", placeholder=_("Pateikties failas")),
            Field("download_url"),
            Field("imported"),
            Field("data_service"),
            Field("upload_to_storage"),
            Field("licence"),
            Field("parent"),
            Field("applicable_legislation"),
            Field("conditions"),
            Field("rights_relation"),
            Field("is_hvd"),
            Submit("submit", button, css_class="button is-primary"),
        )

        if not self.resource:
            if default_licence := Licence.objects.filter(is_default=True).first():
                self.initial["licence"] = default_licence
        else:
            self.initial["applicable_legislation"] = list(
                self.resource.applicable_legislation.values_list("url", flat=True)
            )

        if self.resource and self.resource.metadata.first():
            metadata = self.resource.metadata.first()
            self.initial["access"] = metadata.access
            self.initial["name"] = metadata.name
            self.initial["level"] = metadata.level_given if metadata.level_given is not None else "None"
        else:
            self.initial["level"] = "None"

        if not dataset.type.filter(name="catalog"):
            self.fields["imported"].widget = forms.HiddenInput()

    def clean(self):
        file = self.cleaned_data.get("file")
        url = self.cleaned_data.get("download_url")
        access_url = self.cleaned_data.get("access_url")
        upload = self.cleaned_data.get("upload_to_storage")
        rights_relation = self.cleaned_data.get("rights_relation")
        conditions = self.cleaned_data.get("conditions")

        if file and url:
            raise ValidationError(_("Užpildykit vieną iš pasirinktų laukų: URL lauką arba įkelkit failą, ne abu."))

        if not file and not url and not access_url:
            self.add_error("access_url", _("Pateikite duomenų prieigos nuorodą."))
            self.add_error("download_url", _("Arba pateikite duomenų atsisiuntimo nuorodą."))
            self.add_error("file", _("Arba įkelkite duomenų failą."))

        if url and "get.data.gov.lt" in url and not upload:
            self.cleaned_data["upload_to_storage"] = True

        if url:
            if self.resource:
                distributions_with_same_url = self.dataset.datasetdistribution_set.filter(download_url=url).exclude(
                    pk=self.resource.pk
                )
            else:
                distributions_with_same_url = self.dataset.datasetdistribution_set.filter(download_url=url)
            if distributions_with_same_url.exists():
                self.add_error(
                    "download_url",
                    _("Pateiktis su šia atsisiuntimo nuoroda jau egzistuoja."),
                )

        if rights_relation and conditions:
            self.add_error(
                "conditions",
                _("Užpildykite tik vieną teisių deklaracijų lauką."),
            )
            self.add_error(
                "rights_relation",
                _("Užpildykite tik vieną teisių deklaracijų lauką."),
            )

        return self.cleaned_data

    def clean_access(self):
        access = self.cleaned_data.get("access")
        if access == "":
            return None
        return access

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name:
            if not name.isascii():
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))
            if any(c.isupper() for c in name):
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik mažosios raidės."))
        return name

    def clean_level(self):
        level = self.cleaned_data.get("level")
        if level and level != "None":
            return int(level)
        return None

    def clean_applicable_legislation(self) -> list[str]:
        urls = self.cleaned_data.get("applicable_legislation", []) or []
        validator = URLValidator()

        cleaned = []
        item_errors = []

        for url in urls:
            if not url:
                item_errors.append(None)
                continue

            try:
                validator(url)
                cleaned.append(url)
                item_errors.append(None)
            except ValidationError as e:
                item_errors.append(f"{url}: {e.message}")

        if any(item_errors):
            self.fields["applicable_legislation"].widget.validation_errors = item_errors
            raise ValidationError(_("Yra klaidų sąraše."))

        return cleaned


class FormatAdminForm(forms.ModelForm):
    extension = forms.CharField(label=_("Failo plėtinys"))
    title = forms.CharField(label=_("Pavadinimas"))
    mimetype = forms.CharField(label=_("MIME tipas"))

    class Meta:
        model = Format
        fields = (
            "extension",
            "title",
            "mimetype",
            "rating",
            "uri",
            "media_type_uri",
        )
