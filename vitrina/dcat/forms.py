from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django_select2.forms import Select2Widget, Select2MultipleWidget
from parler.forms import TranslatableModelForm, TranslatedField
from django.utils.translation import gettext_lazy as _

from vitrina.classifiers.models import Concept
from vitrina.datasets.form_helpers import (
    validate_dataset_name,
    validate_applicable_legislation,
    validate_identifier,
    get_contact_form_choices,
    set_default_agent_endpoint_fields,
    validate_agent_endpoint_fields,
    DATA_SERVICE_STANDARD_URI,
)
from vitrina.datasets.models import Dataset, Contact
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
        instance: Dataset | None = self.instance if self.instance and self.instance.pk else None

        if instance:
            self.initial["applicable_legislation"] = list(instance.applicable_legislation.values_list("url", flat=True))

    def clean_applicable_legislation(self) -> list[str]:
        urls = self.cleaned_data.get("applicable_legislation", []) or []

        item_errors = validate_applicable_legislation(urls)

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
        """Populate contact choices grouped by organization."""
        self.fields["contact"].choices = [("", "---------")] + get_contact_form_choices(self.organization)
        self.fields["contact"].initial = self.instance.contact.content_object.id if self.instance.contact else None


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
        instance: Dataset | None = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "dataset-form"
        self.helper.form_tag = False
        self.organization = organization

        if self.language_code == "en":
            self.fields["description"].required = False

        if parent_dataset_id:
            self.fields["parent"].initial = parent_dataset_id
        elif instance:
            parent = instance.get_parent()
            self.fields["parent"].initial = parent
            self.fields["parent"].queryset = self.fields["parent"].queryset.exclude(pk=instance.pk)

        if instance and instance.name:
            self.initial["name"] = instance.name

    def clean_name(self) -> str | None:
        name = self.cleaned_data.get("name")
        validate_dataset_name(
            name=name,
            dataset=self.instance,
            organization=self.organization,
        )

        return name


class InformationSystemResourceForm(ApplicableLegislationFormMixin, BaseResourceForm):
    identifier = forms.CharField(label=_("Identifikatorius"), required=False)

    class Meta:
        model = Dataset
        fields = (
            "parent",
            "name",
            "information_system_importance",
            "information_system_type",
            "description",
            "identifier",
            "information_system_publisher",
            "information_system_creator",
            "title",
            "landing_page",
            "applicable_legislation",
            "conditions",
            "rights_relation",
            "tags",
        )
        widgets = {
            "information_system_importance": Select2Widget,
            "information_system_type": Select2Widget,
            "information_system_publisher": Select2Widget,
            "information_system_creator": Select2Widget,
        }

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(organization, parent_dataset_id, *args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        if instance:
            self.fields["identifier"].initial = instance.identifier if instance.identifier else ""

        self.fields["landing_page"].label = _("Tinklalapis")
        self.fields["landing_page"].help_text = _(
            "Ši savybė nurodo tinklalapį, kuris yra pagrindinis katalogo puslapis. Atitinka foaf:homepage."
        )

        organization_qs = Organization.objects.all()
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

        self.fields["information_system_type"].queryset = Concept.objects.filter(
            concept_schemas__uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
        ).prefetch_related("translations")
        self.fields["information_system_type"].label_from_instance = lambda obj: str(obj.translated_label)

        self.fields["information_system_importance"].required = True
        self.fields["information_system_importance"].queryset = Concept.objects.filter(
            concept_schemas__uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI
        ).prefetch_related("translations")
        self.fields["information_system_importance"].label_from_instance = lambda obj: str(obj.translated_label)

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
        Concept.objects.filter(concept_schemas__uri=DATA_SERVICE_STANDARD_URI).prefetch_related("translations"),
        label=_("Atitinka"),
        required=False,
        help_text=_("Nurodo kokį standartą atitinka paslauga. Atitinka dct:conformsTo."),
        widget=Select2Widget,
    )

    class Meta:
        model = Dataset
        fields = (
            "parent",
            "name",
            "title",
            "agent",  # Either "agent" or "endpoint_url" is required
            "endpoint_url",
            "endpoint_type",  # Not in DCAT. Maybe make non-required?
            "contact",
            "endpoint_description",
            "endpoint_description_type",  # Not in DCAT. Maybe make non-required?
            "tags",
            "access_rights",
            "conforms_to",
            "description",
            "landing_page",
            "service_type",
        )

        widgets = {
            "agent": Select2Widget,
            "endpoint_type": Select2Widget,
            "endpoint_description_type": Select2Widget,
            "access_rights": Select2Widget,
            "service_type": Select2MultipleWidget,
        }

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(organization, parent_dataset_id, *args, **kwargs)

        self.fields["service_type"].queryset = (
            Concept.objects.filter(concept_schemas__uri=Dataset.SERVICE_TYPE_SCHEME_URI)
            .prefetch_related("translations")
            .distinct()
        )
        self.fields["service_type"].label_from_instance = lambda obj: obj.safe_translation_getter(
            "label", any_language=True
        )
        self.fields["description"].required = False
        self.fields["tags"].required = True
        self.fields["agent"].queryset = Agent.objects.not_archived().filter(organization=self.organization)
        self.fields["contact"].required = True

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

    class Meta:
        model = Dataset
        fields = (
            "parent",
            "name",
            "description",
            "title",
            "tags",
            "temporal_start",
            "temporal_end",
            "access_rights",
            "documentation",
            "frequency",
            "landing_page",
            "contact",
            "spatial_resolution",
            "temporal_resolution",
            "applicable_legislation",
        )
        widgets = {
            "access_rights": Select2Widget,
            "frequency": Select2Widget,
            "temporal_start": forms.TextInput(attrs={"type": "date"}),
            "temporal_end": forms.TextInput(attrs={"type": "date"}),
        }

    def __init__(self, organization: Organization, parent_dataset_id: int | None, *args, **kwargs) -> None:
        super().__init__(organization, parent_dataset_id, *args, **kwargs)

        instance: Dataset | None = self.instance if self.instance and self.instance.pk else None
        if instance:
            self.initial["documentation"] = list(instance.documentation.values_list("documentation_link", flat=True))

        self.helper.layout = Layout(
            Field("parent"),
            Field("name"),
            Field("description"),
            Field("title"),
            Field("tags"),
            inline_fields(
                Field("temporal_start"),
                Field("temporal_end"),
            ),
            Field("access_rights"),
            Field("documentation"),
            Field("frequency"),
            Field("landing_page"),
            Field("contact"),
            Field("spatial_resolution"),
            Field("temporal_resolution"),
            Field("applicable_legislation"),
        )

    def clean(self) -> None:
        start = self.cleaned_data.get("temporal_start")
        end = self.cleaned_data.get("temporal_end")
        if start and end and start > end:
            self.add_error(
                "temporal_start",
                _("Laikotarpio pradžios data negali būti vėlesnė nei pabaigos data."),
            )
