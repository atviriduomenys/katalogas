from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Case, When, IntegerField
from django.forms.widgets import URLInput
from django_select2.forms import Select2Widget, Select2MultipleWidget
from parler.forms import TranslatableModelForm

from vitrina.classifiers.models import Concept, Licence
from vitrina.datasets.form_helpers import validate_urls
from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.fields import StringListField
from vitrina.resources.forms import CODE_ORDER
from vitrina.resources.models import DatasetDistribution, DISTRIBUTION_STANDARD_URI

from django.utils.translation import gettext_lazy as _


class DatasetDistributionForm(TranslatableModelForm):
    documentation = StringListField(
        label=_("Puslapis (dokumentacija)"),
        help_text=_("Nuorodos į dokumentus su informacija apie pateiktį. Atitinka foaf:page."),
        required=False,
        unique=True,
    )

    class Meta:
        model = DatasetDistribution
        fields = (
            "name",
            "access_url",
            "availability",
            "title",
            "description",
            "data_service",
            "licence",
            # Medijos tipas (dcat:mediaType) 0..1
            "format",
            "compression_format",
            "packaging_format",
            "size",
            "download_url",
            "checksum_value",
            "checksum_algorithm",
            "issued",
            "date_modified",
            "language",
            "conforms_to",
            "documentation",
            "conditions",
            "rights_relation",
            "spatial_resolution",
            "status",
            "temporal_resolution",
        )
        field_classes = {
            "access_url": forms.URLField,
            "download_url": forms.URLField,
        }
        widgets = {
            "availability": Select2Widget,
            "data_service": Select2Widget,
            "licence": Select2Widget,
            "format": Select2Widget,
            "compression_format": Select2Widget,
            "packaging_format": Select2Widget,
            "checksum_algorithm": Select2Widget,
            "download_url": URLInput,
            "status": Select2Widget,
            "issued": forms.TextInput(attrs={"type": "date"}),
            "date_modified": forms.TextInput(attrs={"type": "date"}),
            "language": Select2Widget,
            "conforms_to": Select2MultipleWidget,
        }

    def __init__(self, dataset: Dataset, *args, **kwargs) -> None:
        self.dataset = dataset
        super().__init__(*args, **kwargs)
        self.resource = self.instance if self.instance and self.instance.pk else None

        button = _("Redaguoti") if self.resource else _("Sukurti")
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "resource-form"
        self.helper.add_input(Submit("submit", button, css_class="button is-primary"))

        self.fields["access_url"].required = True
        self.fields["data_service"].queryset = Dataset.objects.filter(
            is_public=False, subclass__name=DCATResourceSubclass.SERVICE
        ).prefetch_related("translations")
        self.fields["data_service"].required = False
        self.fields["licence"].queryset = self.fields["licence"].queryset.order_by("title")
        self.fields["format"].queryset = self.fields["format"].queryset.order_by("title")
        self.fields["format"].required = False
        self.fields["compression_format"].queryset = self.fields["compression_format"].queryset.order_by("title")
        self.fields["packaging_format"].queryset = self.fields["packaging_format"].queryset.order_by("title")
        self.fields["conforms_to"].queryset = Concept.objects.filter(
            concept_schemas__uri=DISTRIBUTION_STANDARD_URI
        ).prefetch_related("translations")
        self.fields["status"].queryset = (
            Concept.objects.filter(concept_schemas__uri=DatasetDistribution.DISTRIBUTION_STATUS_URI)
            .prefetch_related("translations")
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

        if not self.resource and (default_licence := Licence.objects.filter(is_default=True).first()):
            self.initial["licence"] = default_licence

        if self.resource:
            self.initial["documentation"] = list(
                self.resource.documentation.values_list("documentation_link", flat=True)
            )
            if resource_metadata := self.resource.metadata.first():
                self.initial["name"] = resource_metadata.name

    def clean(self) -> dict:
        if download_url := self.cleaned_data.get("download_url"):
            same_url_dataset_distributions = self.dataset.datasetdistribution_set.filter(download_url=download_url)
            if self.resource:
                same_url_dataset_distributions = same_url_dataset_distributions.exclude(pk=self.resource.pk)

            if same_url_dataset_distributions.exists():
                self.add_error("download_url", _("Duomenų šaltinis su šia atsisiuntimo nuoroda jau egzistuoja."))

        rights_relation = self.cleaned_data.get("rights_relation")
        conditions = self.cleaned_data.get("conditions")
        if rights_relation and conditions:
            self.add_error("conditions", _("Užpildykite tik vieną teisių deklaracijų lauką."))
            self.add_error("rights_relation", _("Užpildykite tik vieną teisių deklaracijų lauką."))

        return self.cleaned_data

    def clean_name(self) -> str:
        if name := self.cleaned_data.get("name"):
            if not name.isascii():
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik lotyniškos raidės."))
            if any(character.isupper() for character in name):
                raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik mažosios raidės."))

        return name

    def clean_checksum_value(self) -> str:
        if (checksum_value := self.cleaned_data.get("checksum_value")) and any(
            character.isupper() for character in checksum_value
        ):
            raise ValidationError(_("Kodiniame pavadinime gali būti naudojamos tik mažosios raidės."))

        return checksum_value

    def clean_documentation(self) -> list[str]:
        documentation_urls = self.cleaned_data.get("documentation", []) or []

        item_errors = validate_urls(documentation_urls)
        if any(item_errors):
            self.fields["documentation"].widget.validation_errors = item_errors
            raise ValidationError(_("Yra klaidų sąraše."))

        return [url for url in documentation_urls if url]  # Remove empty URL rows
