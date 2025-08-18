from django import forms
from django.core.exceptions import ValidationError
from django.forms import DateField
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout
from parler.forms import TranslatedField, TranslatableModelForm

from vitrina.classifiers.models import Licence
from vitrina.datasets.models import Dataset
from vitrina.fields import FilerFileField
from vitrina.helpers import inline_fields
from vitrina.resources.models import DatasetDistribution, Format
from vitrina.structure.models import Metadata
import re

XSD_DURATION_REGEX = re.compile(r"^(-?)P(?=.)((\d+)Y)?((\d+)M)?((\d+)D)?(T(?=.)((\d+)H)?((\d+)M)?(\d*(\.\d+)?S)?)?$")


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
            _(
                "Duomenyse nėra tokio duomenų lauko, kuris unikaliai identifikuoja objektą."
            ),
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
            _(
                "Duomenų lauko, kuris yra parinktas kaip identifikatorius, reikšmės gali keistis."
            ),
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
        label=_("Prieigos lygmuo"), choices=Metadata.ACCESS_TYPES, required=False
    )
    period_start = DateField(
        widget=forms.TextInput(attrs={"type": "date"}),
        required=False,
        label=_("Periodo pradžia"),
        help_text=_("Data nuo kada duomenys yra aktualūs."),
    )
    period_end = DateField(
        widget=forms.TextInput(attrs={"type": "date"}),
        required=False,
        label=_("Periodo pabaiga"),
        help_text=_("Data nuo kada duomenys nebėra aktualūs."),
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

    class Meta:
        model = DatasetDistribution
        fields = (
            "title",
            "description",
            "geo_location",
            "period_start",
            "period_end",
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
            "temporal_resolution",
            "spatial_resolution",
        )

    def __init__(self, dataset, *args, **kwargs):
        self.dataset = dataset
        super().__init__(*args, **kwargs)
        self.resource = self.instance if self.instance and self.instance.pk else None
        button = _("Redaguoti") if self.resource else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "resource-form"
        self.helper.layout = Layout(
            Field(
                "title",
                placeholder=_("Šaltinio pavadinimas"),
                css_class="control is-expanded",
            ),
            Field("description", placeholder=_("Detalus šaltinio aprašas"), rows="2"),
            Field("name"),
            Field("temporal_resolution"),
            Field("spatial_resolution"),
            Field("access"),
            Field("level"),
            Field("is_parameterized"),
            Field("geo_location", placeholder=_("Pateikitę geografinę padėtį")),
            inline_fields(
                Field("period_start", placeholder=_("Pasirinkite pradžios datą")),
                Field("period_end", placeholder=_("Pasirinkite pabaigos datą")),
            ),
            Field("access_url"),
            Field("format"),
            Field("compression_format"),
            Field("packaging_format"),
            Field("file", placeholder=_("Šaltinio failas")),
            Field("download_url"),
            Field("imported"),
            Field("data_service"),
            Field("upload_to_storage"),
            Field("licence"),
            Field("conditions"),
            Submit("submit", button, css_class="button is-primary"),
        )

        if not self.resource:
            if default_licence := Licence.objects.filter(is_default=True).first():
                self.initial["licence"] = default_licence

        if self.resource and self.resource.metadata.first():
            metadata = self.resource.metadata.first()
            self.initial["access"] = metadata.access
            self.initial["name"] = metadata.name
            self.initial["level"] = (
                metadata.level_given if metadata.level_given is not None else "None"
            )
        else:
            self.initial["level"] = "None"

        if not dataset.type.filter(name="catalog"):
            self.fields["imported"].widget = forms.HiddenInput()

    def clean(self):
        file = self.cleaned_data.get("file")
        url = self.cleaned_data.get("download_url")
        access_url = self.cleaned_data.get("access_url")
        upload = self.cleaned_data.get("upload_to_storage")

        if file and url:
            raise ValidationError(
                _(
                    "Užpildykit vieną iš pasirinktų laukų: URL lauką arba "
                    "įkelkit failą, ne abu."
                )
            )

        if not file and not url and not access_url:
            self.add_error("access_url", _("Pateikite duomenų prieigos nuorodą."))
            self.add_error("download_url", _("Arba pateikite duomenų atsisiuntimo nuorodą."))
            self.add_error("file", _("Arba įkelkite duomenų failą."))

        if url and "get.data.gov.lt" in url and not upload:
            self.cleaned_data["upload_to_storage"] = True

        if url:
            if self.resource:
                distributions_with_same_url = (
                    self.dataset.datasetdistribution_set.filter(
                        download_url=url
                    ).exclude(pk=self.resource.pk)
                )
            else:
                distributions_with_same_url = (
                    self.dataset.datasetdistribution_set.filter(download_url=url)
                )
            if distributions_with_same_url.exists():
                self.add_error(
                    "download_url",
                    _("Duomenų šaltinis su šia atsisiuntimo nuoroda jau egzistuoja."),
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
                raise ValidationError(
                    _(
                        "Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."
                    )
                )
            if any(c.isupper() for c in name):
                raise ValidationError(
                    _("Kodiniame pavadinime gali būti naudojamos tik mažosios raidės.")
                )
        return name

    def clean_level(self):
        level = self.cleaned_data.get("level")
        if level and level != "None":
            return int(level)
        return None

    def clean_temporal_resolution(self):
        temporal_resolution = self.cleaned_data.get("temporal_resolution").upper()
        if temporal_resolution and not XSD_DURATION_REGEX.match(temporal_resolution):
                raise ValidationError(_("Laiko skiriamoji geba turi atitikti ISO 8601 reikalavimus, pvz 'P1D', 'PT1H'."))
        return temporal_resolution


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
