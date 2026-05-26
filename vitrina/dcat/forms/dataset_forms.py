from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.shortcuts import get_object_or_404
from django_select2.forms import Select2Widget, Select2MultipleWidget
from parler.forms import TranslatableModelForm, TranslatedField
from django.utils.translation import gettext_lazy as _

from vitrina.classifiers.models import Category, Concept, LANGUAGE_CONCEPT_SCHEMA_URI
from vitrina.datasets.form_helpers import (
    validate_urls,
    validate_identifier,
    get_contact_form_choices,
    set_default_agent_endpoint_fields,
    validate_agent_endpoint_fields,
    DATA_SERVICE_STANDARD_URI,
    DATASET_STANDARD_URI,
)
from vitrina.datasets.helpers import match_name_prefix
from vitrina.datasets.models import (
    Attribution,
    Dataset,
    Contact,
    DCATResourceSubclass,
    Relation,
)
from vitrina.classifiers.models import FormFieldHelpText
from vitrina.dcat.form_helpers import apply_dynamic_help_texts, get_available_dcat_name_prefixes
from vitrina.dcat.widgets import (
    CategoryMultipleWidget,
    DatasetMultipleWidget,
    OrganizationMultipleWidget,
    OrganizationSingleWidget,
)
from vitrina.fields import StringListField
from vitrina.helpers import inline_fields
from vitrina.orgs.models import Organization
from vitrina.uapi.models import Agent


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


class BaseResourceForm(TranslatableModelForm):
    name_prefix = forms.ChoiceField(
        required=False,
        widget=Select2Widget,
        label=_("Kodinio pavadinimo prefiksas"),
        help_text=_(
            "Kodinio pavadinimo prefiksas, kuris kartu su kodiniu pavadinimu sudaro pilną "
            "ištekliaus kodinį pavadinimą. Jei nenurodytas - bus užpildytas automatiškai pagal pasirinktą "
            "tėvinį išteklių arba organizaciją."
        ),
    )
    name = forms.CharField(
        label=_("Kodinis pavadinimas"),
        help_text=_("Duomenų ištekliaus identifikatorius. Atitinka dct:identifier."),
        required=True,
        validators=[
            RegexValidator(
                r"^([a-z]+\/?)+$",
                message=_(
                    "Kodinis pavadinimas turi būti sudarytas iš mažųjų raidžių ir (arba) gali turėti pasvirųjų brūkšnių"
                ),
            )
        ],
    )
    parent = forms.ModelChoiceField(
        Dataset.objects.all().prefetch_related("translations"),
        label=_("Tėvinis išteklius"),
        widget=Select2Widget(),
        required=False,
        help_text=_("Ši savybė nurodo susijusį resursą. Atitinka dct:relation."),
    )
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

        if self.language_code == "en":
            self.fields["description"].required = False

        if url_parent:
            self.fields["parent"].initial = url_parent.pk
        elif self.instance.pk:
            self.fields["parent"].initial = self.instance.get_parent()
            self.fields["parent"].queryset = self.fields["parent"].queryset.exclude(pk=self.instance.pk)

        if self.instance.pk:
            self.initial["category"] = self.instance.category.all()

        instance_name = self.instance.name if self.instance.pk else None
        prefix_source_dataset = self._resolve_prefix_source_dataset(url_parent)
        available_prefixes = get_available_dcat_name_prefixes(prefix_source_dataset, self.organization)
        self._setup_name_prefix_field(available_prefixes, url_parent, instance_name)
        self._setup_name_field(available_prefixes, instance_name)

    def _resolve_prefix_source_dataset(self, url_parent: Dataset | None) -> Dataset | None:
        """Resolves what parent dataset to use when checking available prefixes"""
        if self.data:
            # If form data is being submitted - use value from "parent" field. Even if it's empty
            if submitted_parent_id := self.data.get(self.add_prefix("parent")):
                return get_object_or_404(Dataset, id=submitted_parent_id)
            return None
        if self.instance and self.instance.pk:
            # If form has existing dataset instance - use instance parent
            return self.instance.get_parent()

        # Otherwise use dataset parent given via URL. It may also be None
        return url_parent

    def _setup_name_prefix_field(
        self, available_prefixes: list[str], url_parent: Dataset | None, instance_name: str | None
    ) -> None:
        self.fields["name_prefix"].choices = [(p, p) for p in available_prefixes]
        if not available_prefixes:
            return

        initial_prefix = None
        if instance_name:
            initial_prefix = match_name_prefix(instance_name, available_prefixes)
        elif url_parent and url_parent.name:
            initial_prefix = match_name_prefix(url_parent.name, available_prefixes)

        self.fields["name_prefix"].initial = initial_prefix or available_prefixes[0]

    def _setup_name_field(self, available_prefixes: list[str], instance_name: str | None) -> None:
        if instance_name and available_prefixes:
            prefix = match_name_prefix(instance_name, available_prefixes)
            suffix = instance_name[len(prefix) :] if prefix else instance_name
            self.initial["name"] = suffix.strip("/")

    def get_dataset_name(self) -> str:
        return f"{self.cleaned_data['name_prefix'].removesuffix('/')}/{self.cleaned_data['name']}"

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()

        available_name_prefixes = get_available_dcat_name_prefixes(cleaned_data.get("parent"), self.organization)
        if not available_name_prefixes:
            raise ValidationError(
                _(
                    "Organizacija neturi nurodyto kodinio pavadinimo. Priskirkite kodinį "
                    "pavadinimą organizacijai ir bandykite iš naujo"
                )
            )

        if (name_prefix := cleaned_data.get("name_prefix")) and name_prefix not in available_name_prefixes:
            self.add_error(
                "name_prefix",
                _("Nurodytas kodinio pavadinimo prefiksas turi būti vienas iš: {prefixes}").format(
                    prefixes=", ".join(available_name_prefixes)
                ),
            )
            return cleaned_data

        return cleaned_data


class InformationSystemResourceForm(ApplicableLegislationFormMixin, BaseResourceForm):
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
            "parent",
            "name_prefix",
            "name",
            "information_system_importance",
            "information_system_type",
            "information_system_assessment_url",
            "description",
            "identifier",
            "information_system_publishers",
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

        self.fields["parent"].queryset = self.fields["parent"].queryset.filter(
            organization=self.organization, subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM, is_public=False
        )

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

        self.fields["information_system_importance"].required = True
        self.fields["information_system_importance"].queryset = Concept.ordered_by_label_objects.filter(
            concept_schemas__uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI
        ).prefetch_related("translations")
        self.fields["information_system_importance"].label_from_instance = lambda obj: str(obj.translated_label)

        self.fields["information_system_assessment_url"].required = True

        self.fields["languages"].queryset = Concept.ordered_by_label_objects.filter(
            concept_schemas__uri=LANGUAGE_CONCEPT_SCHEMA_URI
        ).prefetch_related("translations")
        self.fields["languages"].label_from_instance = lambda obj: str(obj.translated_label)

        self.helper.layout = Layout(
            Field("parent"),
            Field("name_prefix"),
            Field("information_system_importance"),
            Field("information_system_type"),
            Field("information_system_assessment_url"),
            Field("description"),
            Field("title"),
            Field("name"),
            Field("tags"),
            Field("category"),
            Field("identifier"),
            Field("information_system_publishers"),
            Field("creator"),
            Field("landing_page"),
            Field("languages"),
            Field("conditions"),
            Field("rights_relation"),
            Field("applicable_legislation"),
        )

        apply_dynamic_help_texts(self, FormFieldHelpText.DCAT_INFORMATION_SYSTEM)

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


class ServiceResourceForm(ContactFormMixin, BaseResourceForm):
    endpoint_url = forms.CharField(
        label=_("API adresas"),
        required=False,
        help_text=_("Laisvu tekstu pateikiamas duomenų paslaugos galinio taško URL. Atitinka dcat:endpointURL."),
    )
    endpoint_description = forms.CharField(
        label=_("API specifikacija"),
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
            "parent",
            "name_prefix",
            "name",
            "title",
            "agent",  # Either "agent" or "endpoint_url" is required
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
            "agent": Select2Widget,
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

        self.fields["parent"].queryset = self.fields["parent"].queryset.filter(
            organization=self.organization, subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM, is_public=False
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
        self.fields["tags"].required = True
        self.fields["agent"].queryset = Agent.objects.not_archived().filter(organization=self.organization)
        self.fields["license"].queryset = self.fields["license"].queryset.order_by("title")

        apply_dynamic_help_texts(self, FormFieldHelpText.DCAT_SERVICE)

        self.helper.layout = Layout(
            Field("parent"),
            Field("name_prefix"),
            Field("name"),
            Field("title"),
            Field("organization"),
            Field("agent"),
            Field("endpoint_url"),
            Field("endpoint_type"),
            Field("contact"),
            Field("endpoint_description"),
            Field("endpoint_description_type"),
            Field("tags"),
            Field("category"),
            Field("access_rights"),
            Field("conforms_to"),
            Field("description"),
            Field("follows"),
            Field("landing_page"),
            Field("license"),
            Field("service_quality"),
            Field("service_type"),
        )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()

        cleaned_data = set_default_agent_endpoint_fields(cleaned_data)

        errors = validate_agent_endpoint_fields(
            agent=cleaned_data.get("agent"),
            conforms_to=cleaned_data.get("conforms_to"),
            endpoint_url=cleaned_data.get("endpoint_url"),
            endpoint_type=cleaned_data.get("endpoint_type"),
            endpoint_description=cleaned_data.get("endpoint_description"),
            endpoint_description_type=cleaned_data.get("endpoint_description_type"),
        )
        for field_name, error_message in errors:
            self.add_error(field_name, error_message)

        return cleaned_data


class DatasetResourceForm(ApplicableLegislationFormMixin, ContactFormMixin, BaseResourceForm):
    documentation = StringListField(
        label=_("Dokumentacija"),
        help_text=_("Ši savybė nurodo puslapį apie šį duomenų rinkinį. Atitinka foaf:page."),
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
            "parent",
            "name_prefix",
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
            "was_generated_by": Select2MultipleWidget,
        }

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)

        self.fields["parent"].queryset = self.fields["parent"].queryset.filter(
            organization=self.organization, subclass__name=DCATResourceSubclass.SERVICE, is_public=False
        )

        self.fields["organization"].required = True
        self.fields["organization"].label = _("Duomenų skelbėjas")
        self.fields["organization"].help_text = _("Duomenų skelbėjas. Atitinka dct:publisher.")

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

        self.helper.layout = Layout(
            Field("parent"),
            Field("name_prefix"),
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
            Field("contact"),
            Field("landing_page"),
            Field("languages"),
            Field("qualified_relation"),
            Field("provenance"),
            Field("spatial_resolution"),
            Field("temporal_resolution"),
            Field("dataset_type"),
            Field("version_notes"),
            Field("was_generated_by"),
            Field("applicable_legislation"),
        )

        apply_dynamic_help_texts(self, FormFieldHelpText.DCAT_DATASET)

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
    has_part = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.CATALOG),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Priklauso duomenų katalogams"),
        help_text=_(
            "Ši savybė nurodo susijusius katalogus, kurie yra aprašyto katalogo dalis. "
            "Pildoma, kai institucijos turi nuosavus metaduomenų katalogus. Atitinka dct:hasPart."
        ),
    )
    related_information_system = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Susijusios informacinės sistemos (teikia duomenis į)"),
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
        label=_("Susijusios informacinės sistemos (gauna duomenis iš)"),
        help_text=_(
            "Informacinės sistemos, kurios teikia duomenis šiai IS. Susijusios sistemos yra tos, kurios turi "
            "integracijas ir yra įvardintos nuostatuose. Atitinka dcataplt:relatesToInformationSystem."
        ),
    )

    class Meta:
        model = Dataset
        fields = InformationSystemResourceForm.Meta.fields + (
            "has_part",
            "related_information_system",
            "relates_to_information_system",
        )
        widgets = InformationSystemResourceForm.Meta.widgets

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)
        self.helper.layout.extend(
            [
                Field("has_part"),
                Field("related_information_system"),
                Field("relates_to_information_system"),
            ]
        )
        if self.instance.pk:
            self.fields["identifier"].initial = self.instance.identifier or ""
            self.initial["has_part"] = self.fields["has_part"].queryset.filter(
                related_datasets__relation__name=Relation.CATALOG,
                related_datasets__dataset=self.instance,
            )
            self.initial["relates_to_information_system"] = self.fields["related_information_system"].queryset.filter(
                dataset_relations__relation__name=Relation.RELATES_TO_INFORMATION_SYSTEM,
                dataset_relations__part_of=self.instance,
            )
            self.initial["related_information_system"] = self.fields["relates_to_information_system"].queryset.filter(
                related_datasets__relation__name=Relation.RELATES_TO_INFORMATION_SYSTEM,
                related_datasets__dataset=self.instance,
            )
            creator_attribution = self.instance.datasetattribution_set.filter(
                attribution__name=Attribution.CREATOR
            ).first()
            if creator_attribution:
                self.initial["creator"] = creator_attribution.organization_id


class ServiceUpdateForm(ServiceResourceForm):
    serves_datasets = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.DATASET),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Pateikia duomenų rinkinius"),
        help_text=_("Duomenų paslaugos teikiami duomenų rinkiniai. Atitinka dct:servesDataset."),
    )

    class Meta:
        model = Dataset
        fields = ServiceResourceForm.Meta.fields + ("serves_datasets",)
        widgets = ServiceResourceForm.Meta.widgets

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)
        self.helper.layout.append(Field("serves_datasets"))
        if self.instance.pk:
            self.initial["serves_datasets"] = self.fields["serves_datasets"].queryset.filter(
                related_datasets__relation__name=Relation.SERVICE,
                related_datasets__dataset=self.instance,
            )


class DatasetUpdateForm(DatasetResourceForm):
    qualified_attribution = forms.ModelMultipleChoiceField(
        queryset=Organization.objects.all(),
        widget=OrganizationMultipleWidget(),
        required=False,
        label=_("Kvalifikuotas priskyrimas"),
        help_text=_("Organizacija atsakinga už šį duomenų rinkinį. Atitinka prov:qualifiedAttribution."),
    )

    class Meta:
        model = Dataset
        fields = DatasetResourceForm.Meta.fields + ("qualified_attribution",)
        widgets = DatasetResourceForm.Meta.widgets

    def __init__(self, organization: Organization, url_parent: Dataset | None, *args, **kwargs) -> None:
        super().__init__(organization, url_parent, *args, **kwargs)
        if self.instance.pk:
            self.initial["documentation"] = list(
                self.instance.documentation.values_list("documentation_link", flat=True)
            )
            self.initial["qualified_relation"] = list(self.instance.qualified_relations.values_list("url", flat=True))
            self.initial["qualified_attribution"] = self.instance.datasetattribution_set.filter(
                attribution__name=Attribution.CONTRIBUTOR
            ).values_list("organization_id", flat=True)
            creator_attribution = self.instance.datasetattribution_set.filter(
                attribution__name=Attribution.CREATOR
            ).first()
            if creator_attribution:
                self.initial["creator"] = creator_attribution.organization_id

        self.helper.layout.append(Field("qualified_attribution"))


class InformationSystemRelationshipForm(forms.Form):
    has_part = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.CATALOG),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Priklauso duomenų katalogams"),
        help_text=_(
            "Ši savybė nurodo susijusius katalogus, kurie yra aprašyto katalogo dalis. "
            "Pildoma, kai institucijos turi nuosavus metaduomenų katalogus. Atitinka dct:hasPart."
        ),
    )
    related_information_system = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Susijusios informacinės sistemos (teikia duomenis į)"),
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
        label=_("Susijusios informacinės sistemos (gauna duomenis iš)"),
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
        self.helper.layout = Layout(
            Field("has_part"),
            Field("related_information_system"),
            Field("relates_to_information_system"),
        )


class ServiceRelationshipForm(forms.Form):
    serves_datasets = forms.ModelMultipleChoiceField(
        queryset=Dataset.objects.filter(subclass__name=DCATResourceSubclass.DATASET),
        widget=DatasetMultipleWidget(),
        required=False,
        label=_("Pateikia duomenų rinkinius"),
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
        self.helper.layout = Layout(
            Field("serves_datasets"),
        )


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
        self.helper.layout = Layout(
            Field("qualified_attribution"),
        )
