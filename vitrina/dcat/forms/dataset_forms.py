from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django_select2.forms import Select2Widget, Select2MultipleWidget
from parler.forms import TranslatableModelForm, TranslatedField
from django.utils.translation import gettext_lazy as _

from vitrina.classifiers.models import Concept, LANGUAGE_CONCEPT_SCHEMA_URI
from vitrina.datasets.form_helpers import (
    validate_dataset_name,
    validate_urls,
    validate_identifier,
    get_contact_form_choices,
    set_default_agent_endpoint_fields,
    validate_agent_endpoint_fields,
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
from vitrina.dcat.widgets import DatasetMultipleWidget, OrganizationMultipleWidget, OrganizationSingleWidget
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
    name = forms.CharField(
        label=_("Kodinis pavadinimas"),
        help_text=_("Duomenų ištekliaus identifikatorius. Atitinka dct:identifier."),
        required=True,
        validators=[
            RegexValidator(
                "([a-z]+\/?)+",
                message="Kodinis pavadinimas turi būti sudarytas iš mažųjų raidžių ir (arba) gali turėti pasvirųjų brūkšnių",
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
    description = TranslatedField(required=True)
    title = TranslatedField(
        form_class=forms.CharField,
        required=True,
        widget=forms.TextInput(),
    )

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "dataset-form"
        self.helper.form_tag = False
        self.organization = organization

        if self.language_code == "en":
            self.fields["description"].required = False

        if parent_dataset_id:
            self.fields["parent"].initial = parent_dataset_id
        elif self.instance.pk:
            self.fields["parent"].initial = self.instance.get_parent()
            self.fields["parent"].queryset = self.fields["parent"].queryset.exclude(pk=self.instance.pk)

        if self.instance.pk and self.instance.name:
            self.initial["name"] = self.instance.name

    def clean_name(self) -> str | None:
        name = self.cleaned_data.get("name")
        validate_dataset_name(
            name=name,
            dataset=self.instance,
            organization=self.organization,
        )

        return name


class InformationSystemResourceForm(ApplicableLegislationFormMixin, BaseResourceForm):
    identifier = forms.CharField(
        label=_("Identifikatorius"),
        required=True,
        help_text=_("RISR (registrai.lt) IS identifikavimo kodas. Atitinka dct:identifier."),
    )

    class Meta:
        model = Dataset
        fields = (
            "parent",
            "name",
            "information_system_importance",
            "information_system_type",
            "information_system_assessment_url",
            "description",
            "identifier",
            "information_system_publisher",
            "information_system_creator",
            "title",
            "landing_page",
            "languages",
            "conditions",
            "rights_relation",
            "applicable_legislation",
            "tags",
        )
        widgets = {
            "information_system_importance": Select2Widget,
            "information_system_type": Select2Widget,
            "information_system_publisher": Select2Widget,
            "information_system_creator": Select2Widget,
            "languages": Select2MultipleWidget,
        }

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(organization, parent_dataset_id, *args, **kwargs)

        self.fields["parent"].queryset = self.fields["parent"].queryset.filter(
            organization=self.organization, subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM, is_public=False
        )

        self.fields["landing_page"].label = _("Tinklalapis")
        self.fields["landing_page"].help_text = _(
            "Ši savybė nurodo tinklalapį, kuris yra pagrindinis katalogo puslapis. Atitinka foaf:homepage."
        )

        organization_qs = Organization.objects.all().order_by("title")
        self.fields["information_system_publisher"].queryset = organization_qs
        self.fields["information_system_publisher"].required = True
        self.fields["information_system_publisher"].help_text = _(
            "Ši savybė nurodo subjektą (organizaciją), atsakingą už IS prieinamumą. Atitinka dct:publisher"
        )
        self.fields["information_system_creator"].queryset = organization_qs
        self.fields["information_system_creator"].required = True
        self.fields["information_system_creator"].help_text = _(
            "Subjektas, atsakingas už IS parengimą. Atitinka dct:creator"
        )

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

    def clean(self) -> None:
        rights_relation = self.cleaned_data.get("rights_relation")
        conditions = self.cleaned_data.get("conditions")
        if rights_relation and conditions:
            self.add_error("conditions", _("Užpildykite tik vieną teisių deklaracijų lauką."))
            self.add_error("rights_relation", _("Užpildykite tik vieną teisių deklaracijų lauką."))

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

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(organization, parent_dataset_id, *args, **kwargs)

        self.fields["parent"].queryset = self.fields["parent"].queryset.filter(
            organization=self.organization, subclass__name=DCATResourceSubclass.INFORMATION_SYSTEM, is_public=False
        )

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
            "name",
            "description",
            "title",
            "tags",
            "organization",
            "temporal_start",
            "temporal_end",
            "access_rights",
            "conforms_to",
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

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(organization, parent_dataset_id, *args, **kwargs)

        self.fields["parent"].queryset = self.fields["parent"].queryset.filter(
            organization=self.organization, subclass__name=DCATResourceSubclass.SERVICE, is_public=False
        )

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
            Field("name"),
            Field("description"),
            Field("title"),
            Field("tags"),
            Field("organization"),
            inline_fields(
                Field("temporal_start"),
                Field("temporal_end"),
            ),
            Field("access_rights"),
            Field("conforms_to"),
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

    def clean_qualified_relation(self) -> list[str]:
        urls = self.cleaned_data.get("qualified_relation", []) or []
        item_errors = validate_urls(urls)
        if any(item_errors):
            self.fields["qualified_relation"].widget.validation_errors = item_errors
            raise ValidationError(_("Yra klaidų sąraše."))
        return [url for url in urls if url]

    def clean(self) -> None:
        start = self.cleaned_data.get("temporal_start")
        end = self.cleaned_data.get("temporal_end")
        if start and end and start > end:
            self.add_error(
                "temporal_start",
                _("Laikotarpio pradžios data negali būti vėlesnė nei pabaigos data."),
            )


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

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(organization, parent_dataset_id, *args, **kwargs)
        self.fields["identifier"].initial = self.instance.identifier or ""
        if self.instance.pk:
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

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(organization, parent_dataset_id, *args, **kwargs)
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

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(organization, parent_dataset_id, *args, **kwargs)
        self.initial["documentation"] = list(self.instance.documentation.values_list("documentation_link", flat=True))
        self.initial["qualified_relation"] = list(self.instance.qualified_relations.values_list("url", flat=True))
        if self.instance.pk:
            self.initial["qualified_attribution"] = self.instance.datasetattribution_set.filter(
                attribution__name=Attribution.CONTRIBUTOR
            ).values_list("organization_id", flat=True)

        self.helper.layout.append(Field("qualified_attribution"))
