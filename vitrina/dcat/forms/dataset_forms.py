from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django_select2.forms import Select2Widget, Select2MultipleWidget
from parler.forms import TranslatableModelForm, TranslatedField
from django.utils.translation import gettext_lazy as _

from vitrina.classifiers.models import Category, Concept, LANGUAGE_CONCEPT_SCHEMA_URI
from vitrina.datasets.form_helpers import (
    validate_urls,
    validate_identifier,
    get_contact_form_choices,
    DATA_SERVICE_STANDARD_URI,
    DATASET_STANDARD_URI,
)
from vitrina.datasets.models import (
    Attribution,
    Dataset,
    Contact,
    DCATResourceSubclass,
    Relation,
)
from vitrina.identifiers.models import Agency
from vitrina.classifiers.models import FormFieldText
from vitrina.dcat.form_helpers import apply_dynamic_help_texts
from vitrina.dcat.widgets import (
    CategoryMultipleWidget,
    DatasetMultipleWidget,
    OrganizationMultipleWidget,
    OrganizationSingleWidget,
)
from vitrina.fields import StringListField
from vitrina.helpers import inline_fields
from vitrina.orgs.models import Organization


class ApplicableLegislationFormMixin(forms.Form):
    applicable_legislation = StringListField(
        label=_("Teisinis pagrindas"),
        help_text=_(
            "Teisės aktas, kurio pagrindu yra valdomas ir tvarkomas duomenų rinkinys.<br>"
            "Norint nurodyti konkrečią vietą teisės akto dokumente, po „#“ pateikite konkrečią nuorodą, "
            "pvz., „#17.2“.<br>"
            "Tais atvejais, kai yra keli dokumentai su priedais: „#priedas1/17.2“, „17.2/17.2.5“, "
            "kur „priedas1“ yra dokumento failo pavadinimas.<br>"
            "Atitinka dcatap:applicableLegislation."
        ),
        required=False,
        unique=True,
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["applicable_legislation"] = list(
                self.instance.applicable_legislation.values_list("url", flat=True)
            )

    def clean_applicable_legislation(self) -> list[str]:
        urls = self.cleaned_data.get("applicable_legislation", []) or []

        item_errors = validate_urls(urls)

        if any(item_errors):
            self.fields["applicable_legislation"].widget.validation_errors = item_errors
            raise ValidationError(_("Yra klaidų sąraše."))

        return [url for url in urls if url]  # Remove empty URL rows


class ContactFormMixin(forms.Form):
    contact = forms.ChoiceField(
        label=_("Kontaktinis asmuo ar organizacija"),
        help_text=_(
            "Kontaktinė informacija, kurią galima naudoti siunčiant pastabas apie duomenų išteklių. Atitinka dcat:contactPoint."
        ),
        required=False,
        widget=Select2Widget,
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._populate_contact_choices()

    def clean_contact(self) -> Contact | None:
        if contact := self.cleaned_data.get("contact"):
            return Contact.objects.get(pk=contact)
        return None

    def _populate_contact_choices(self) -> None:
        self.fields["contact"].choices = [("", "---------")] + get_contact_form_choices(self.organization)
        if self.instance.pk:
            self.fields["contact"].initial = (
                self.instance.contact.content_object.id
                if self.instance.contact and self.instance.contact.content_object
                else None
            )


class DatasetNameMixin(forms.Form):
    codename_preview = forms.CharField(
        disabled=True,
        required=False,
        label=_("Pilnas kodinis pavadinimas"),
        help_text=_("Pilnas kodinis pavadinimas, sudarytas iš prefikso ir kodinio pavadinimo."),
    )
    name = forms.CharField(
        label=_("Kodinis pavadinimas"),
        help_text=_("Duomenų ištekliaus kodinis pavadinimas"),
        required=True,
        validators=[
            RegexValidator(
                r"^([a-z_]+\/?)+$",
                message=_(
                    "Kodinis pavadinimas turi būti sudarytas iš mažųjų lotyniškų raidžių ir (arba) apatinių brūkšnių, žodžius atskiriant apatiniais brūkšniais"
                ),
            )
        ],
    )

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)

        organization_codename = self.organization.name or ""
        if self.instance.pk:
            parent = self.instance.get_parent()
            self.codename_prefix = parent.name if parent else organization_codename
        else:
            self.codename_prefix = url_parent.name if url_parent else organization_codename

        if self.instance.pk:
            # For update, we set initial name from instance, not from parent
            codename_preview = self.instance.name or ""
            self.initial["name"] = codename_preview.removeprefix(self.codename_prefix).strip("/")
            self.initial["codename_preview"] = codename_preview
        else:
            self.initial["codename_preview"] = f"{self.codename_prefix}" if self.codename_prefix else ""

    def get_dataset_name(self) -> str:
        return f"{self.codename_prefix.removesuffix('/')}/{self.cleaned_data['name']}"

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if not self.codename_prefix:
            raise ValidationError(
                _(
                    "Organizacija neturi nurodyto kodinio pavadinimo. Priskirkite kodinį "
                    "pavadinimą organizacijai ir bandykite iš naujo"
                )
            )
        return cleaned_data


class BaseResourceForm(TranslatableModelForm):
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.order_by("title"),
        label=_("Kategorija"),
        help_text=_("Nurodo vieną ar kelias kategorijas. Atitinka dcat:theme."),
        widget=CategoryMultipleWidget,
        required=False,
    )
    description = TranslatedField(required=True)
    title = TranslatedField(
        form_class=forms.CharField,
        required=True,
        widget=forms.TextInput(),
    )

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "dataset-form"
        self.helper.form_tag = False
        self.organization = organization
        self.codename_prefix = ""

        if self.language_code == "en":
            self.fields["description"].required = False

        if self.instance.pk:
            self.initial["category"] = self.instance.category.all()


class InformationSystemResourceForm(ApplicableLegislationFormMixin, DatasetNameMixin, BaseResourceForm):
    identifier = forms.CharField(
        label=_("Identifikatorius"),
        required=True,
        help_text=_("RISR (registrai.lt) IS identifikavimo kodas. Atitinka dct:identifier."),
    )
    creator = forms.ModelChoiceField(
        Organization.objects.all(),
        required=True,
        label=_("Valdytojas"),
        help_text=_("Institucija, pagal nuostatus IS valdytoja. Atitinka dct:creator."),
        widget=OrganizationSingleWidget,
    )

    class Meta:
        model = Dataset
        fields = (
            "codename_preview",
            "name",
            "information_system_importance",
            "information_system_type",
            "information_system_assessment_url",
            "description",
            "identifier",
            "information_system_publishers",
            "creator",
            "title",
            "landing_page",
            "languages",
            "category",
            "conditions",
            "rights_relation",
            "applicable_legislation",
            "tags",
        )
        widgets = {
            "information_system_importance": Select2Widget,
            "information_system_type": Select2Widget,
            "information_system_publishers": Select2MultipleWidget,
            "languages": Select2MultipleWidget,
        }

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)

        self.fields["landing_page"].label = _("Tinklalapis")
        self.fields["landing_page"].help_text = _(
            "Ši savybė nurodo tinklalapį, kuris yra pagrindinis katalogo puslapis. Atitinka foaf:homepage."
        )

        organization_qs = Organization.objects.all().order_by("title")
        self.fields["information_system_publishers"].queryset = organization_qs
        self.fields["information_system_publishers"].required = True
        self.fields["creator"].queryset = organization_qs

        self.fields["information_system_type"].queryset = Concept.ordered_by_label_objects.filter(
            concept_schemas__uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
        ).prefetch_related("translations")
        self.fields["information_system_type"].label_from_instance = lambda obj: str(obj.translated_label)
        self.fields["information_system_type"].label = _("Informacinės sistemos rūšis")

        self.fields["information_system_importance"].required = True
        self.fields["information_system_importance"].queryset = Concept.ordered_by_label_objects.filter(
            concept_schemas__uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI
        ).prefetch_related("translations")
        self.fields["information_system_importance"].label_from_instance = lambda obj: str(obj.translated_label)

        self.fields["information_system_assessment_url"].required = True

        self.fields["description"].label = _("Aprašas")

        self.fields["languages"].queryset = Concept.ordered_by_label_objects.filter(
            concept_schemas__uri=LANGUAGE_CONCEPT_SCHEMA_URI
        ).prefetch_related("translations")
        self.fields["languages"].label_from_instance = lambda obj: str(obj.translated_label)

        apply_dynamic_help_texts(self, FormFieldText.DCAT_INFORMATION_SYSTEM)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        rights_relation = cleaned_data.get("rights_relation")
        conditions = cleaned_data.get("conditions")
        if rights_relation and conditions:
            self.add_error("conditions", _("Užpildykite tik vieną teisių deklaracijų lauką."))
            self.add_error("rights_relation", _("Užpildykite tik vieną teisių deklaracijų lauką."))
        return cleaned_data

    def clean_identifier(self) -> str:
        identifier = self.cleaned_data.get("identifier")
        validate_identifier(identifier)

        return identifier


class ServiceResourceForm(ContactFormMixin, DatasetNameMixin, BaseResourceForm):
    endpoint_url = forms.CharField(
        label=_("Tinklapis"),
        required=False,
        help_text=_("Laisvu tekstu pateikiamas duomenų paslaugos galinio taško URL. Atitinka dcat:endpointURL."),
    )
    endpoint_description = forms.CharField(
        label=_("Prieigos taško aprašas"),
        required=False,
        help_text=_(
            "Šioje savybėje pateikiamas paslaugų, prieinamų per galinius taškus, aprašymas. "
            "Įskaitant jų operacijas, parametrus ir t. t. Atitinka dcat:endpointDescription."
        ),
    )
    conforms_to = forms.ModelChoiceField(
        Concept.ordered_by_label_objects.filter(concept_schemas__uri=DATA_SERVICE_STANDARD_URI).prefetch_related(
            "translations"
        ),
        label=_("Atitinka"),
        required=False,
        help_text=_("Nurodo kokį standartą atitinka paslauga. Atitinka dct:conformsTo."),
        widget=Select2Widget,
    )
    service_quality = StringListField(
        label=_("Paslaugos kokybė"),
        help_text=_("Tinklalapis su išsamia informacija apie teikiamos paslaugos kokybę. Atitinka foaf:page."),
        required=False,
        unique=True,
    )

    class Meta:
        model = Dataset
        fields = (
            "codename_preview",
            "name",
            "title",
            "endpoint_url",
            "endpoint_type",  # Not in DCAT
            "contact",
            "endpoint_description",
            "endpoint_description_type",  # Not in DCAT
            "tags",
            "organization",
            "category",
            "access_rights",
            "conforms_to",
            "description",
            "follows",
            "landing_page",
            "license",
            "service_quality",
            "service_type",
        )

        widgets = {
            "endpoint_type": Select2Widget,
            "endpoint_description_type": Select2Widget,
            "organization": OrganizationSingleWidget,
            "access_rights": Select2Widget,
            "follows": Select2MultipleWidget,
            "license": Select2Widget,
            "service_type": Select2MultipleWidget,
        }

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)

        self.fields["name"].label = _("Identifikatorius")
        self.fields["name"].help_text = _(
            "Institucijos vidinis duomenų paslaugos identifikatorius. Formatas: kod_pav. Atitinka dct:identifier."
        )
        self.fields["codename_preview"].label = _("Pilnas identifikatorius")
        self.fields["codename_preview"].help_text = _(
            "Pilnas identifikatorius, sudarytas iš tėvinio ištekliaus identifikatoriaus ir šios "
            "duomenų paslaugos identifikatoriaus."
        )

        self.fields["contact"].label = _("Kontaktinė informacija")
        self.fields["contact"].help_text = _(
            "Kontaktinė informacija, kurią galima naudoti siunčiant pastabas apie duomenų paslaugą. "
            "Atitinka dcat:contactPoint."
        )

        self.fields["organization"].required = True
        self.fields["organization"].label = _("Duomenų teikėjas")
        self.fields["organization"].help_text = _("Duomenų teikėjas. Atitinka dct:publisher.")

        self.fields["service_type"].queryset = (
            Concept.ordered_by_label_objects.filter(concept_schemas__uri=Dataset.SERVICE_TYPE_SCHEME_URI)
            .prefetch_related("translations")
            .distinct()
        )
        self.fields["service_type"].label_from_instance = lambda obj: obj.safe_translation_getter(
            "label", any_language=True
        )
        self.fields["description"].required = False
        self.fields["description"].label = _("Aprašas")
        self.fields["tags"].required = True
        self.fields["tags"].label = _("Raktažodis / žyma")
        self.fields["category"].label = _("Tema / kategorija")
        self.fields["landing_page"].label = _("Nukreipimo puslapis")
        self.fields["license"].queryset = self.fields["license"].queryset.order_by("title")

        apply_dynamic_help_texts(self, FormFieldText.DCAT_SERVICE)


class DatasetResourceForm(ApplicableLegislationFormMixin, ContactFormMixin, DatasetNameMixin, BaseResourceForm):
    documentation = StringListField(
        label=_("Dokumentacija"),
        help_text=_("Ši savybė nurodo puslapį apie šį duomenų rinkinį. Atitinka foaf:page."),
        required=False,
        unique=True,
    )
    was_generated_by = StringListField(
        label=_("Buvo sukurtas dėl"),
        help_text=_("Veikla, dėl kurios buvo sukurtas duomenų rinkinys. Atitinka prov:wasGeneratedBy."),
        required=False,
        unique=True,
    )
    conforms_to = forms.ModelChoiceField(
        Concept.ordered_by_label_objects.filter(concept_schemas__uri=DATASET_STANDARD_URI).prefetch_related(
            "translations"
        ),
        label=_("Atitinka"),
        required=False,
        help_text=_("Nurodo kokį standartą atitinka duomenų rinkinys. Atitinka dct:conformsTo."),
        widget=Select2Widget,
    )
    creator = forms.ModelChoiceField(
        Organization.objects.all(),
        required=False,
        label=_("Atsakingas subjektas"),
        help_text=_("Organizacija, atsakinga už duomenų rinkinio sukūrimą. Atitinka dct:creator."),
        widget=OrganizationSingleWidget,
    )
    qualified_relation = StringListField(
        label=_("Kvalifikuotas ryšys"),
        help_text=_(
            "Nuoroda į susijusį dokumentą, kuriame aprašytas šis duomenų rinkinys. "
            "Įprastai IS techninė specifikacija. Atitinka dcat:qualifiedRelation."
        ),
        required=False,
        unique=True,
    )

    class Meta:
        model = Dataset
        fields = (
            "codename_preview",
            "name",
            "description",
            "title",
            "tags",
            "organization",
            "temporal_start",
            "temporal_end",
            "category",
            "access_rights",
            "conforms_to",
            "creator",
            "documentation",
            "frequency",
            "landing_page",
            "contact",
            "languages",
            "qualified_relation",
            "provenance",
            "spatial_resolution",
            "temporal_resolution",
            "dataset_type",
            "version_notes",
            "was_generated_by",
            "applicable_legislation",
            "has_quality_annotation",
            "has_quality_measurement",
        )
        widgets = {
            "organization": OrganizationSingleWidget,
            "temporal_start": forms.TextInput(attrs={"type": "date"}),
            "temporal_end": forms.TextInput(attrs={"type": "date"}),
            "access_rights": Select2Widget,
            "frequency": Select2Widget,
            "languages": Select2MultipleWidget,
            "provenance": Select2MultipleWidget,
            "dataset_type": Select2Widget,
            "has_quality_annotation": Select2Widget,
            "has_quality_measurement": Select2Widget,
        }

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)

        self.fields["codename_preview"].help_text = _(
            "Pilnas URI, pagal https://ivpk.github.io/uapi/#section/Concepts/URI, identifikuojantis duomenų rinkinį."
        )
        self.fields["name"].label = _("Identifikatorius")
        self.fields["name"].help_text = _(
            "Duomenų rinkinio viešinimui naudojamas identifikatorius. Naudoti mažąsias lotyniškas raides, "
            'žodžius atskirti žemu brūkšniu "_". Pvz.: kod_pav. Atitinka dct:identifier'
        )

        self.fields["tags"].label = _("Raktažodis")
        self.fields["frequency"].label = _("Kaupimo periodiškumas")

        self.fields["organization"].required = True
        self.fields["organization"].label = _("Duomenų skelbėjas")
        self.fields["organization"].help_text = _("Duomenų skelbėjas. Atitinka dct:publisher.")

        self.fields["landing_page"].label = _("Nukreipimo puslapis")

        self.fields["contact"].label = _("Kontaktas")
        self.fields["contact"].help_text = _("Nurodo kontaktą susisiekti dėl duomenų rinkinio. Atitinka vcard:Kind.")

        self.fields["dataset_type"].queryset = (
            Concept.ordered_by_label_objects.filter(concept_schemas__uri=Dataset.DATASET_TYPE_SCHEME_URI)
            .prefetch_related("translations")
            .distinct()
        )
        self.fields["dataset_type"].label_from_instance = lambda obj: obj.safe_translation_getter(
            "label", any_language=True
        )
        self.fields["languages"].queryset = Concept.ordered_by_label_objects.filter(
            concept_schemas__uri=LANGUAGE_CONCEPT_SCHEMA_URI
        ).prefetch_related("translations")
        self.fields["languages"].label_from_instance = lambda obj: obj.safe_translation_getter(
            "label", any_language=True
        )

        if self.instance.pk:
            self.initial["was_generated_by"] = list(self.instance.was_generated_by.values_list("title", flat=True))

        self.fields["has_quality_annotation"].label = _("Turi kokybės anotaciją")
        self.fields["has_quality_annotation"].help_text = _(
            "Nurodo, kiek nuoseklus yra duomenų rinkinys visoje sistemoje. Atitinka dqv:hasQualityAnnotation."
        )
        self.fields["has_quality_measurement"].label = _("Turi kokybės matavimą")
        self.fields["has_quality_measurement"].help_text = _(
            "Nurodo, kaip patikimas yra pateiktas duomenų rinkinys. Atitinka dqv:hasQualityMeasurement."
        )

        self.helper.layout = Layout(
            Field("codename_preview"),
            Field("name"),
            Field("description"),
            Field("title"),
            Field("tags"),
            Field("organization"),
            inline_fields(
                Field("temporal_start"),
                Field("temporal_end"),
            ),
            Field("category"),
            Field("access_rights"),
            Field("conforms_to"),
            Field("creator"),
            Field("documentation"),
            Field("frequency"),
            Field("landing_page"),
            Field("contact"),
            Field("languages"),
            Field("provenance"),
            Field("qualified_relation"),
            Field("spatial_resolution"),
            Field("temporal_resolution"),
            Field("dataset_type"),
            Field("version_notes"),
            Field("was_generated_by"),
            Field("applicable_legislation"),
            Field("has_quality_annotation"),
            Field("has_quality_measurement"),
        )

        apply_dynamic_help_texts(self, FormFieldText.DCAT_DATASET)

    def clean_qualified_relation(self) -> list[str]:
        urls = self.cleaned_data.get("qualified_relation", []) or []
        item_errors = validate_urls(urls)
        if any(item_errors):
            self.fields["qualified_relation"].widget.validation_errors = item_errors
            raise ValidationError(_("Yra klaidų sąraše."))
        return [url for url in urls if url]

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        start = cleaned_data.get("temporal_start")
        end = cleaned_data.get("temporal_end")
        if start and end and start > end:
            self.add_error(
                "temporal_start",
                _("Laikotarpio pradžios data negali būti vėlesnė nei pabaigos data."),
            )
        return cleaned_data


class InformationSystemUpdateForm(InformationSystemResourceForm):
    class Meta:
        model = Dataset
        fields = InformationSystemResourceForm.Meta.fields
        widgets = InformationSystemResourceForm.Meta.widgets

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)
        if self.instance.pk:
            self.fields["identifier"].initial = self.instance.identifier or ""
            creator_attribution = self.instance.datasetattribution_set.filter(
                attribution__name=Attribution.CREATOR
            ).first()
            if creator_attribution:
                self.initial["creator"] = creator_attribution.organization_id


class ServiceUpdateForm(ServiceResourceForm):
    class Meta:
        model = Dataset
        fields = ServiceResourceForm.Meta.fields
        widgets = ServiceResourceForm.Meta.widgets


class DatasetUpdateForm(DatasetResourceForm):
    class Meta:
        model = Dataset
        fields = DatasetResourceForm.Meta.fields
        widgets = DatasetResourceForm.Meta.widgets

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)
        if self.instance.pk:
            self.initial["documentation"] = list(
                self.instance.documentation.values_list("documentation_link", flat=True)
            )
            self.initial["qualified_relation"] = list(self.instance.qualified_relations.values_list("url", flat=True))
            creator_attribution = self.instance.datasetattribution_set.filter(
                attribution__name=Attribution.CREATOR
            ).first()
            if creator_attribution:
                self.initial["creator"] = creator_attribution.organization_id


class ISPublicServiceResourceForm(ContactFormMixin, BaseResourceForm):
    identifier = forms.CharField(
        label=_("Identifikatorius"),
        required=True,
        help_text=_(
            "PASIS kodas. Jei nėra - institucijos suteiktas vidinis teikiamos paslaugos identifikatorius "
            "arba sveikas skaičius. Atitinka dct:identifier."
        ),
    )

    class Meta:
        model = Dataset
        fields = (
            "title",
            "identifier",
            "description",
            "information_system_publishers",
            "landing_page",
            "spatial_coverages",
            "is_public_service_status",
            "service_type",
            "category",
            "follows",
            "contact",
        )
        widgets = {
            "information_system_publishers": Select2MultipleWidget,
            "spatial_coverages": Select2MultipleWidget,
            "is_public_service_status": Select2Widget,
            "service_type": Select2MultipleWidget,
            "follows": Select2MultipleWidget,
        }

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)

        self._parent = self.instance.get_parent() if self.instance.pk else url_parent

        self.fields["information_system_publishers"].required = True
        self.fields["information_system_publishers"].queryset = self.fields[
            "information_system_publishers"
        ].queryset.order_by("title")
        self.fields["information_system_publishers"].label = _("Turi kompetentingą valdžios instituciją")
        self.fields["information_system_publishers"].help_text = _(
            "Viešojo administravimo institucijos, atsakingos už šią paslaugą. Atitinka cv:hasCompetentAuthority."
        )

        self.fields["landing_page"].required = True
        self.fields["landing_page"].label = _("Pagrindinis puslapis")
        self.fields["landing_page"].help_text = _("Pagrindinis e. paslaugos tinklalapis. Atitinka foaf:homepage.")

        self.fields["service_type"].queryset = (
            Concept.ordered_by_label_objects.filter(concept_schemas__uri=Dataset.SERVICE_TYPE_SCHEME_URI)
            .prefetch_related("translations")
            .distinct()
        )
        self.fields["service_type"].label_from_instance = lambda obj: obj.safe_translation_getter(
            "label", any_language=True
        )

        self.fields["is_public_service_status"].queryset = (
            Concept.ordered_by_label_objects.filter(concept_schemas__uri=Dataset.IS_PUBLIC_SERVICE_STATUS_SCHEME_URI)
            .prefetch_related("translations")
            .distinct()
        )
        self.fields["is_public_service_status"].label_from_instance = lambda obj: obj.safe_translation_getter(
            "label", any_language=True
        )

        self.fields["category"].label = _("Tematinė sritis")
        self.fields["category"].help_text = _("E. paslaugos tema. Atitinka skos:concept.")

        self.fields["contact"].label = _("Turi kontaktinę informaciją")
        self.fields["contact"].help_text = _(
            "Su e. paslaugos teikimu susijusi kontaktinė informacija. Atitinka cv:hasContactPoint."
        )

        apply_dynamic_help_texts(self, FormFieldText.DCAT_IS_PUBLIC_SERVICE)

    def get_dataset_name(self) -> str:
        parent_name = self._parent.name if self._parent else self.organization.name or ""
        return f"{parent_name.removesuffix('/')}/{self.cleaned_data['identifier']}"


class ISPublicServiceUpdateForm(ISPublicServiceResourceForm):
    class Meta:
        model = Dataset
        fields = ISPublicServiceResourceForm.Meta.fields
        widgets = ISPublicServiceResourceForm.Meta.widgets

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)
        if self.instance.pk:
            pasis_identifier = self.instance.identifiers.filter(scheme_agency__code=Agency.PASIS_CODE).first()
            self.fields["identifier"].initial = pasis_identifier.notation if pasis_identifier else ""


class InformationSystemRelationshipForm(forms.Form):
    has_part = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(
            subclass__name__in=[DCATResourceSubclass.CATALOG, DCATResourceSubclass.INFORMATION_SYSTEM]
        ),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Turi sudedamąją dalį"),
        help_text=_(
            "Ši savybė nurodo susijusius katalogus, kurie yra aprašyto katalogo dalis. "
            "Pildoma, kai institucijos turi nuosavus metaduomenų katalogus. Atitinka dct:hasPart."
        ),
    )
    related_information_system = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Susijusi IS"),
        help_text=_(
            "Informacinės sistemos, kurios domina ar yra susijusios su šia informacinė sistema. Susijusios "
            "sistemos yra tos, kurios turi integracijas ir yra įvardintos nuostatuose. "
            "Atitinka dcataplt:informationSystem."
        ),
    )
    relates_to_information_system = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Susijusi IS"),
        help_text=_(
            "Informacinės sistemos, kurios teikia duomenis šiai IS. Susijusios sistemos yra tos, kurios turi "
            "integracijas ir yra įvardintos nuostatuose. Atitinka dcataplt:relatesToInformationSystem."
        ),
    )

    def __init__(self, dataset: Dataset, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if dataset.pk:
            self.initial["has_part"] = Dataset.objects.filter(
                related_datasets__relation__name=Relation.CATALOG,
                related_datasets__dataset=dataset,
            )
            self.initial["related_information_system"] = Dataset.objects.filter(
                related_datasets__relation__name=Relation.RELATES_TO_INFORMATION_SYSTEM,
                related_datasets__dataset=dataset,
            )
            self.initial["relates_to_information_system"] = Dataset.objects.filter(
                dataset_relations__relation__name=Relation.RELATES_TO_INFORMATION_SYSTEM,
                dataset_relations__part_of=dataset,
            )
        self.helper = FormHelper()
        self.helper.form_tag = False
        apply_dynamic_help_texts(self, FormFieldText.DCAT_IS_RELATIONSHIPS)


class ServiceRelationshipForm(forms.Form):
    serves_datasets = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.DATASET),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Pateikia duomenų rinkinį"),
        help_text=_("Duomenų paslaugos teikiami duomenų rinkiniai. Atitinka dct:servesDataset."),
    )

    def __init__(self, dataset: Dataset, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if dataset.pk:
            self.initial["serves_datasets"] = Dataset.objects.filter(
                related_datasets__relation__name=Relation.SERVICE,
                related_datasets__dataset=dataset,
            )
        self.helper = FormHelper()
        self.helper.form_tag = False
        apply_dynamic_help_texts(self, FormFieldText.DCAT_SERVICE_RELATIONSHIPS)


class DatasetRelationshipForm(forms.Form):
    qualified_attribution = forms.ModelMultipleChoiceField(
        queryset=Organization.objects.all(),
        widget=OrganizationMultipleWidget(),
        required=False,
        label=_("Kvalifikuotas priskyrimas"),
        help_text=_("Organizacija atsakinga už šį duomenų rinkinį. Atitinka prov:qualifiedAttribution."),
    )

    def __init__(self, dataset: Dataset, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if dataset.pk:
            self.initial["qualified_attribution"] = dataset.datasetattribution_set.filter(
                attribution__name=Attribution.CONTRIBUTOR
            ).values_list("organization_id", flat=True)
        self.helper = FormHelper()
        self.helper.form_tag = False
        apply_dynamic_help_texts(self, FormFieldText.DCAT_DATASET_RELATIONSHIPS)


class ISPublicServiceRelationshipForm(forms.Form):
    produces_datasets = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.DATASET),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Sukuria duomenų rinkinį"),
        help_text=_("Duomenų rinkiniai, kuriuos sukuria ši e. paslauga. Atitinka cpsv:produces."),
    )
    produces_services = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.SERVICE),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Sukuria duomenų paslaugą"),
        help_text=_("Paslaugos, kurias sukuria ši e. paslauga. Atitinka cpsv:produces."),
    )
    produces_catalogs = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.CATALOG),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Sukuria katalogą"),
        help_text=_("Katalogai, kuriuos sukuria ši e. paslauga. Atitinka cpsv:produces."),
    )

    def __init__(self, dataset: Dataset, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if dataset.pk:
            produced = Dataset.objects.filter(
                related_datasets__relation__name=Relation.PRODUCES,
                related_datasets__dataset=dataset,
            )
            self.initial["produces_datasets"] = produced.filter(subclass__name=DCATResourceSubclass.DATASET)
            self.initial["produces_services"] = produced.filter(subclass__name=DCATResourceSubclass.SERVICE)
            self.initial["produces_catalogs"] = produced.filter(subclass__name=DCATResourceSubclass.CATALOG)
        self.helper = FormHelper()
        self.helper.form_tag = False
