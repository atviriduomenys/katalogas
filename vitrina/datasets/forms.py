from datetime import date
from typing import Any

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.handlers.wsgi import WSGIRequest
from django.core.validators import RegexValidator
from django.db.models import Value, CharField as _CharField, Case, When, Count, Q
from django.db.models.functions import Concat
from django.utils.safestring import mark_safe
from django_select2.forms import ModelSelect2Widget, Select2Widget
from parler.forms import TranslatableModelForm, TranslatedField
from parler.views import TranslatableModelFormMixin
from django import forms
from django.forms import (
    TextInput,
    CharField,
    DateField,
    ModelMultipleChoiceField,
    Form,
    ModelChoiceField,
    CheckboxSelectMultiple,
    HiddenInput,
)
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Submit, Layout, HTML
from haystack.forms import FacetedSearchForm
from treebeard.forms import MoveNodeForm

from vitrina.datasets.form_helpers import (
    validate_dataset_name,
    validate_urls,
    validate_identifier,
    get_contact_form_choices,
    DATA_SERVICE_STANDARD_URI,
    set_default_agent_endpoint_fields,
    validate_agent_endpoint_fields,
)
from vitrina.datasets.services import get_requests
from vitrina.classifiers.models import Frequency, Category, Concept

from vitrina.fields import FilerFileField, MultipleFilerField, StringListField
from vitrina.helpers import get_current_domain, inline_fields
from vitrina.orgs.forms import (
    RepresentativeCreateForm,
    RepresentativeUpdateForm,
    OrganizationPlanForm,
)

from vitrina.datasets.models import (
    Dataset,
    DatasetStructure,
    DatasetGroup,
    DatasetAttribution,
    DatasetRelation,
    Relation,
    Contact,
    DCATResourceSubclass,
)
from vitrina.orgs.models import Organization
from vitrina.plans.models import PlanDataset, Plan
from vitrina.users.models import User
from vitrina.projects.services import get_projects_linkable_to_dataset
from vitrina.uapi.models import Agent


class ResourceSubclassTypeField(ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.description:
            return mark_safe(f'{obj.title}<br/><p class="help">{obj.description}</p>')
        else:
            return obj.title


class ResourceSubclassForm(TranslatableModelForm, TranslatableModelFormMixin):
    subclass = ResourceSubclassTypeField(
        label=_("Duomenų ištekliaus rūšis"),
        queryset=DCATResourceSubclass.objects.all(),
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Dataset
        fields = ("subclass",)

    def __init__(self, request=None, organization=None, *args, **kwargs):
        self.request = request
        self.organization = organization
        super().__init__(*args, **kwargs)

        instance = self.instance if self.instance and self.instance.pk else None
        user = request.user

        if parent_id := request.resolver_match.kwargs.get("parent_id"):
            parent = Dataset.objects.filter(pk=parent_id).first()
        elif instance:
            parent = instance.get_parent()
        else:
            parent = None

        if user and (user.is_open_data_representative_for(parent or self.organization)):
            self.fields["subclass"].queryset = DCATResourceSubclass.objects.exclude(
                name=DCATResourceSubclass.INFORMATION_SYSTEM
            )

    def clean_subclass(self):
        subclass = self.cleaned_data.get("subclass")
        if not subclass:
            raise ValidationError(_("Šis laukas yra privalomas."))
        return subclass


class BaseResourceForm(TranslatableModelForm):
    title = TranslatedField(
        form_class=CharField,
        required=True,
        widget=TextInput(),
    )
    description = TranslatedField(required=True)
    files = MultipleFilerField(
        label=_("Dokumentacija"),
        help_text=_("Ši savybė nurodo dokumentą apie šį duomenų rinkinį. Atitinka foaf:page."),
        required=False,
        upload_to=Dataset.UPLOAD_TO,
        allow_empty_file=True,
    )
    documentation = StringListField(
        label=_("Dokumentacija"),
        help_text=_("Ši savybė nurodo puslapį apie šį duomenų rinkinį. Atitinka foaf:page."),
        required=False,
        unique=True,
    )
    name = forms.CharField(
        label=_("Kodinis pavadinimas"),
        help_text=_("Duomenų ištekliaus identifikatorius. Atitinka dct:identifier."),
        required=False,
        validators=[
            RegexValidator(
                "([a-z]+\/?)+",
                message="Kodinis pavadinimas turi būti sudarytas iš mažųjų raidžių ir (arba) gali turėti pasvirųjų brūkšnių",
            )
        ],
    )

    contact = forms.ChoiceField(
        label=_("Kontaktinis asmuo ar organizacija"),
        help_text=_(
            "Kontaktinė informacija, kurią galima naudoti siunčiant pastabas apie duomenų išteklių. Atitinka dcat:contactPoint."
        ),
        required=False,
    )

    organization = forms.ModelChoiceField(
        queryset=Organization.public.all().order_by("title"),
        label=_("Paslaugų teikėjas"),
        help_text=_(
            "Ši savybė nurodo subjektą (organizaciją), atsakingą už duomenų ištekliaus prieinamumą. Atitinka dct:publisher."
        ),
        widget=Select2Widget(),
        empty_label=None,
    )

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

    parent = forms.ModelChoiceField(
        Dataset.objects.all(),
        label=_("Tėvinis išteklius"),
        widget=Select2Widget(),
        required=False,
        empty_label=None,
        help_text=_("Ši savybė nurodo susijusį resursą. Atitinka dct:relation."),
    )

    def __init__(
        self,
        request: WSGIRequest,
        organization: Organization | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        instance: Dataset | None = self.instance if self.instance and self.instance.pk else None
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "dataset-form"
        self.helper.form_tag = False
        self.organization = organization

        parent = None

        if parent_id := request.resolver_match.kwargs.get("parent_id"):
            self.fields["parent"].initial = parent_id
            self.fields["parent"].widget = forms.HiddenInput()
            parent = Dataset.objects.filter(pk=parent_id).first()
        elif instance:
            parent = instance.get_parent()
            self.fields["parent"].initial = parent
            self.fields["parent"].queryset = Dataset.objects.exclude(pk=instance.pk)

        self.fields["access_rights"].required = True

        if self.language_code == "en":
            self.fields["description"].required = False
        organization = self.organization if self.organization else instance.organization

        is_open_data_representative = request.user and (
            request.user.is_open_data_representative_for(instance or parent or organization)
        )

        if is_open_data_representative:
            self.fields["access_rights"].choices = [
                (Dataset.PUBLIC, _("Vieši")),
                (Dataset.RESTRICTED, _("Apriboti")),
            ]

        if instance:
            self.initial["files"] = list(instance.dataset_files.values_list("file", flat=True))
            if instance.name:
                self.initial["name"] = instance.name

            self.initial["applicable_legislation"] = list(instance.applicable_legislation.values_list("url", flat=True))
            self.initial["documentation"] = list(instance.documentation.values_list("documentation_link", flat=True))

        else:
            if default_frequency := Frequency.objects.filter(is_default=True).first():
                self.initial["frequency"] = default_frequency

        self.fields["organization"].initial = self.instance.organization or organization
        if not request.user.is_superuser:
            self.fields["organization"].disabled = True
            self.fields["organization"].widget.attrs["style"] = "background-color: #f2f2f2;"

        self._populate_contact_choices()

    def _populate_contact_choices(self) -> None:
        """Populate contact choices grouped by organization."""
        organization = self.instance.organization or self.organization
        self.fields["contact"].choices = [("", "---------")] + get_contact_form_choices(organization)

        if contact := self._get_contact(self.instance):
            self.fields["contact"].initial = contact.id

    @staticmethod
    def _get_contact(instance: Dataset):
        if contact := instance.contact:
            return contact.content_object
        return None

    def clean_name(self) -> str | None:
        name = self.cleaned_data.get("name")
        dataset_instance = self.instance

        validate_dataset_name(
            name=name,
            dataset=self.instance,
            organization=self.organization or dataset_instance.organization,
        )

        return name

    def clean_contact(self) -> Organization | User | None:
        if contact := self.cleaned_data.get("contact"):
            return Contact.objects.get(pk=contact)
        return None

    def clean_applicable_legislation(self) -> list[str]:
        urls = self.cleaned_data.get("applicable_legislation", []) or []

        item_errors = validate_urls(urls)

        if any(item_errors):
            self.fields["applicable_legislation"].widget.validation_errors = item_errors
            raise ValidationError(_("Yra klaidų sąraše."))

        return [url for url in urls if url]  # Remove empty URL rows


class ServiceResourceForm(BaseResourceForm):
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
        Concept.objects.filter(concept_schemas__uri=DATA_SERVICE_STANDARD_URI),
        label=_("Atitinka"),
        required=False,
        help_text=_("Nurodo kokį standartą atitinka paslauga. Atitinka dct:conformsTo."),
    )

    class Meta:
        model = Dataset
        fields = (
            "title",
            "description",
            "is_public",
            "tags",
            "catalog",
            "agent",
            "access_rights",
            "endpoint_url",
            "endpoint_type",
            "endpoint_description",
            "endpoint_description_type",
            "name",
            "contact",
            "organization",
            "landing_page",
            "parent",
            "service_type",
            "is_hvd",
            "conforms_to",
        )

    def __init__(self, request=None, organization=None, *args, **kwargs):
        super().__init__(request, organization, *args, **kwargs)

        self.fields["service_type"].queryset = Concept.objects.filter(
            concept_schemas__uri=Dataset.SERVICE_TYPE_SCHEME_URI
        ).distinct()
        self.fields["service_type"].label_from_instance = lambda obj: obj.safe_translation_getter(
            "label", any_language=True
        )
        self.fields["description"].required = False
        self.fields["tags"].required = True
        self.fields["contact"].required = True
        organization = self.organization if self.organization else self.instance.organization
        self.fields["agent"].queryset = Agent.objects.not_archived().filter(organization=organization)
        self.helper.layout = Layout(
            Field("is_public", placeholder=_("Ar duomenys vieši?")),
            Field("title", placeholder=_("Duomenų rinkinio pavadinimas")),
            Field("name", placeholder=_("Duomenų rinkinio kodinis pavadinimas")),
            Field("description", placeholder=_("Detalus duomenų rinkinio aprašas")),
            Field("service_type"),
            Field("tags", placeholder=_("Surašykite aktualius raktinius žodžius")),
            Field("landing_page"),
            Field("catalog"),
            Field("agent"),
            Field("conforms_to"),
            Field("endpoint_url"),
            Field("endpoint_type"),
            Field("endpoint_description"),
            Field("endpoint_description_type"),
            Field("access_rights"),
            Field("contact"),
            Field("organization"),
            Field("parent"),
            Field("applicable_legislation"),
            Field("is_hvd"),
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


class CatalogResourceForm(BaseResourceForm):
    class Meta:
        model = Dataset
        fields = (
            "title",
            "description",
            "is_public",
            "tags",
            "catalog",
            "frequency",
            "access_rights",
            "name",
            "contact",
            "organization",
            "landing_page",
            "conditions",
            "rights_relation",
        )

    def __init__(self, request=None, organization=None, *args, **kwargs):
        super().__init__(request, organization, *args, **kwargs)
        self.helper.layout = Layout(
            Field("is_public", placeholder=_("Ar duomenys vieši?")),
            Field("title", placeholder=_("Metaduomenų katalogo pavadinimas")),
            Field("name", placeholder=_("Metaduomenų katalogo kodinis pavadinimas")),
            Field("description", placeholder=_("Detalus metaduomenų katalogo aprašas")),
            Field("files"),
            Field("tags", placeholder=_("Surašykite aktualius raktinius žodžius")),
            Field("landing_page"),
            Field("catalog"),
            Field("frequency"),
            Field("access_rights"),
            Field("contact"),
            Field("organization"),
            Field("conditions"),
            Field("rights_relation"),
        )

    def clean(self) -> None:
        rights_relation = self.cleaned_data.get("rights_relation")
        conditions = self.cleaned_data.get("conditions")
        if rights_relation and conditions:
            self.add_error("conditions", _("Užpildykite tik vieną teisių deklaracijų lauką."))
            self.add_error("rights_relation", _("Užpildykite tik vieną teisių deklaracijų lauką."))


class InformationSystemResourceForm(CatalogResourceForm):
    identifier = forms.CharField(label=_("Identifikatorius"), required=False)

    class Meta:
        model = Dataset
        fields = (
            "title",
            "description",
            "is_public",
            "tags",
            "catalog",
            "frequency",
            "access_rights",
            "name",
            "contact",
            "organization",
            "landing_page",
            "information_system_type",
            "information_system_importance",
            "information_system_publisher",
            "information_system_creator",
            "applicable_legislation",
            "conditions",
            "rights_relation",
        )
        widgets = {
            "information_system_publisher": Select2Widget,
            "information_system_creator": Select2Widget,
        }

    def __init__(self, request=None, organization=None, *args, **kwargs):
        super().__init__(request, organization, *args, **kwargs)
        instance = self.instance if self.instance and self.instance.pk else None
        if instance:
            self.fields["identifier"].initial = instance.identifier if instance.identifier else ""

        self.helper.layout = Layout(
            Field("is_public", placeholder=_("Ar duomenys vieši?")),
            Field("title", placeholder=_("Informacinės sistemos pavadinimas")),
            Field("name", placeholder=_("Informacinės sistemos kodinis pavadinimas")),
            Field("description", placeholder=_("Detalus informacinės sistemos aprašas")),
            Field("identifier", placeholder=_("Informacinės sistemos identifikatorius")),
            Field("tags", placeholder=_("Surašykite aktualius raktinius žodžius")),
            Field("landing_page"),
            Field("catalog"),
            Field("frequency"),
            Field("access_rights"),
            Field("contact"),
            Field("organization"),
            Field("information_system_type"),
            Field("information_system_importance"),
            Field("information_system_publisher"),
            Field("information_system_creator"),
            Field("parent"),
            Field("applicable_legislation"),
            Field("conditions"),
            Field("rights_relation"),
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

        self.fields["information_system_type"].queryset = Concept.objects.filter(
            concept_schemas__uri=Dataset.INFORMATION_SYSTEM_TYPE_SCHEMA_URI
        )
        self.fields["information_system_type"].label_from_instance = lambda obj: str(obj.translated_label)
        self.fields["information_system_importance"].required = True
        self.fields["information_system_importance"].queryset = Concept.objects.filter(
            concept_schemas__uri=Dataset.INFORMATION_SYSTEM_IMPORTANCE_SCHEMA_URI
        )
        self.fields["information_system_importance"].label_from_instance = lambda obj: str(obj.translated_label)

    def clean(self):
        super().clean()

    def clean_identifier(self) -> str:
        identifier = self.cleaned_data.get("identifier")
        validate_identifier(identifier)

        return identifier


class DatasetResourceForm(BaseResourceForm):
    temporal_start = DateField(
        widget=forms.TextInput(attrs={"type": "date"}),
        required=False,
        label=_("Laikotarpio pradžia"),
        help_text=_("Duomenų rinkinio laikotarpio pradžia. Atitinka dct:temporal."),
    )
    temporal_end = DateField(
        widget=forms.TextInput(attrs={"type": "date"}),
        required=False,
        label=_("Laikotarpio pabaiga"),
        help_text=_("Duomenų rinkinio laikotarpio pabaiga. Atitinka dct:temporal."),
    )

    class Meta:
        model = Dataset
        fields = (
            "title",
            "description",
            "temporal_start",
            "temporal_end",
            "is_public",
            "tags",
            "catalog",
            "frequency",
            "access_rights",
            "files",
            "documentation",
            "name",
            "contact",
            "organization",
            "landing_page",
            "parent",
            "temporal_resolution",
            "spatial_resolution",
            "is_hvd",
        )

    def __init__(self, request=None, organization=None, *args, **kwargs) -> None:
        super().__init__(request, organization, *args, **kwargs)

        self.helper.layout = Layout(
            Field("is_public", placeholder=_("Ar duomenys vieši")),
            Field("title", placeholder=_("Duomenų rinkinio pavadinimas")),
            Field("name", placeholder=_("Duomenų rinkinio kodinis pavadinimas")),
            Field("description", placeholder=_("Detalus duomenų rinkinio aprašas")),
            inline_fields(
                Field("temporal_start", placeholder=_("Pasirinkite pradžios datą")),
                Field("temporal_end", placeholder=_("Pasirinkite pabaigos datą")),
            ),
            Field("temporal_resolution"),
            Field("spatial_resolution"),
            Field("files"),
            Field("documentation"),
            Field("tags", placeholder=_("Surašykite aktualius raktinius žodžius")),
            Field("landing_page"),
            Field("catalog"),
            Field("frequency"),
            Field("access_rights"),
            Field("contact"),
            Field("organization"),
            Field("parent"),
            Field("applicable_legislation"),
            Field("is_hvd"),
        )

    def clean(self) -> None:
        start = self.cleaned_data.get("temporal_start")
        end = self.cleaned_data.get("temporal_end")
        if start and end and start > end:
            self.add_error(
                "temporal_start",
                _("Laikotarpio pradžios data negali būti vėlesnė nei pabaigos data."),
            )


class ResourceForm(BaseResourceForm):
    class Meta:
        model = Dataset
        fields = (
            "title",
            "description",
            "is_public",
            "tags",
            "catalog",
            "frequency",
            "access_rights",
            "files",
            "name",
            "contact",
            "organization",
            "landing_page",
            "parent",
            "temporal_resolution",
            "spatial_resolution",
            "is_hvd",
        )

    def __init__(self, request=None, organization=None, *args, **kwargs):
        super().__init__(request, organization, *args, **kwargs)

        self.helper.layout = Layout(
            Field("is_public", placeholder=_("Ar duomenys vieši?")),
            Field("title", placeholder=_("Duomenų rinkinio pavadinimas")),
            Field("name", placeholder=_("Duomenų rinkinio kodinis pavadinimas")),
            Field("description", placeholder=_("Detalus duomenų rinkinio aprašas")),
            Field("files"),
            Field("tags", placeholder=_("Surašykite aktualius raktinius žodžius")),
            Field("landing_page"),
            Field("catalog"),
            Field("frequency"),
            Field("access_rights"),
            Field("contact"),
            Field("organization"),
            Field("parent"),
            Field("applicable_legislation"),
            Field("is_hvd"),
        )


class DatasetAdminForm(forms.ModelForm):
    organization = forms.ModelChoiceField(
        queryset=Organization.public.all(),
        label=_("Organizacija"),
    )

    class Meta:
        model = Dataset
        exclude = (
            "slug",
            "current_structure",
            "depth",
            "numchild",
            "path",
            "publisher",
        )


class DatasetSearchForm(FacetedSearchForm):
    date_from = DateField(required=False)
    date_to = DateField(required=False)

    def search(self):
        sqs = super().search()
        sqs = sqs.models(Dataset)
        if not self.is_valid():
            return self.no_query_found()
        if self.cleaned_data.get("q"):
            keyword = self.cleaned_data.get("q")
            if len(keyword) < 5:
                sqs = sqs.autocomplete(text__startswith=keyword)
            else:
                sqs = sqs.autocomplete(text__icontains=keyword)

            dataset_with_name_ids = (
                self.searchqueryset.models(Dataset).filter(name__icontains=keyword).values_list("pk", flat=True)
            )
            dataset_with_model_name_ids = (
                self.searchqueryset.models(Dataset).filter(model_names__icontains=keyword).values_list("pk", flat=True)
            )
            sqs_ids = sqs.values_list("pk", flat=True)
            ids = list(dataset_with_model_name_ids) + list(dataset_with_name_ids) + list(sqs_ids)

            sqs = self.searchqueryset.models(Dataset).filter(id__in=ids)

        if self.cleaned_data.get("date_from"):
            sqs = sqs.filter(published__gte=self.cleaned_data["date_from"])
        if self.cleaned_data.get("date_to"):
            sqs = sqs.filter(published__lte=self.cleaned_data["date_to"])
        return sqs

    def no_query_found(self):
        return self.searchqueryset.all()


class DatasetStructureImportForm(forms.ModelForm):
    file = FilerFileField(label=_("Failas"), required=True, upload_to=DatasetStructure.UPLOAD_TO)

    class Meta:
        model = DatasetStructure
        fields = ("file",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "dataset-structure-form"
        self.helper.layout = Layout(
            Field("file"),
            Submit("submit", _("Patvirtinti"), css_class="button is-primary"),
        )


class OrganizationWidget(ModelSelect2Widget):
    model = Organization
    search_fields = ["title__icontains"]
    max_results = 10

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)
        queryset = queryset.annotate(attribution_count=Count("datasetattribution")).order_by("-attribution_count")
        return queryset


class DatasetAttributionForm(forms.ModelForm):
    organization = forms.ModelChoiceField(
        label=_("Organizacija"),
        required=False,
        queryset=Organization.public.all(),
        widget=OrganizationWidget(attrs={"data-minimum-input-length": 0}),
    )

    class Meta:
        model = DatasetAttribution
        fields = (
            "attribution",
            "organization",
            "agent",
        )

    def __init__(self, dataset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset = dataset

        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "attribution-form"
        self.helper.layout = Layout(
            Field("attribution"),
            Field("organization"),
            Field("agent"),
            Submit("submit", _("Sukurti"), css_class="button is-primary"),
        )

    def clean(self):
        attribution = self.cleaned_data.get("attribution")
        organization = self.cleaned_data.get("organization")
        agent = self.cleaned_data.get("agent")

        if organization and agent:
            self.add_error(
                "organization",
                _('Negalima užpildyti abiejų "Organizacija" ir "Agentas" laukų.'),
            )

        elif not organization and not agent:
            self.add_error(
                "organization",
                _('Privaloma užpildyti "Organizacija" arba "Agentas" lauką.'),
            )

        elif (
            organization
            and DatasetAttribution.objects.filter(
                dataset=self.dataset,
                organization=organization,
                attribution=attribution,
            ).exists()
        ):
            self.add_error(
                "organization",
                _(f'Ryšys "{attribution}" su šia organizacija jau egzistuoja.'),
            )

        elif (
            agent
            and DatasetAttribution.objects.filter(
                dataset=self.dataset,
                agent=agent,
                attribution=attribution,
            ).exists()
        ):
            self.add_error("agent", _(f'Ryšys "{attribution}" su šiuo agentu jau egzistuoja.'))

        return self.cleaned_data


class AddProjectForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ["projects"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.dataset = kwargs.pop("dataset", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "dataset-add-project-form"
        self.fields["projects"].queryset = get_projects_linkable_to_dataset(self.user).exclude(datasets=self.dataset)
        self.helper.layout = Layout(
            Field("projects"),
            Submit("submit", _("Pridėti"), css_class="button is-primary"),
        )

    projects = ModelMultipleChoiceField(
        label=_("Panaudojimo atvejai"),
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text=_("Pažymėkite panaudojimo atvejus, kuriuose yra naudojamas šis duomenų rinkinys."),
    )


class AddRequestForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ["requests"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.dataset = kwargs.pop("dataset", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "dataset-add-request-form"
        self.fields["requests"].queryset = get_requests(self.user, self.dataset)
        self.helper.layout = Layout(
            Field("requests"),
            Submit("submit", _("Pridėti"), css_class="button is-primary"),
        )

    requests = ModelMultipleChoiceField(
        label=_("Poreikiai"),
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text=_("Pažymėkite poreikius, kuriuose yra naudojamas šis duomenų rinkinys."),
    )


class DatasetMemberUpdateForm(RepresentativeUpdateForm):
    object_model = Dataset


class DatasetMemberCreateForm(RepresentativeCreateForm):
    object_model = Dataset


class DatasetCategoryForm(Form):
    search = CharField(label=_("Paieška"), required=False)
    group = ModelMultipleChoiceField(
        label=_("Grupės"),
        required=False,
        queryset=DatasetGroup.objects.all(),
        widget=CheckboxSelectMultiple,
    )
    category = ModelMultipleChoiceField(
        label=_("Kategorija"),
        required=False,
        queryset=Category.objects.all(),
        widget=CheckboxSelectMultiple,
    )

    def __init__(self, dataset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dataset = dataset

        self.helper = FormHelper()
        self.helper.form_id = "dataset-category-form"
        self.helper.layout = Layout(
            Field("group"),
            Field("search"),
            HTML(
                f'<div class="mt-4 mb-3"><input type="checkbox" id="show_selected_id"/>'
                f"<strong>{_('Rodyti pasirinktas kategorijas')}</strong></div>"
            ),
            Field("category"),
            Submit("submit", _("Išsaugoti"), css_class="button is-primary"),
        )

        category_choices = MoveNodeForm.mk_dropdown_tree(Category)
        category_choices = category_choices[1:]
        self.fields["category"].choices = category_choices
        self.initial["category"] = self.dataset.category.all()

        self.initial["group"] = DatasetGroup.objects.filter(
            datasetgroupcategoryuri__category__in=self.dataset.category.all()
        ).distinct()


class PartOfWidget(ModelSelect2Widget):
    model = Dataset
    search_fields = ["translations__title__icontains", "absolute_url__icontains"]
    dependent_fields = {"organization_id": "organization__pk"}
    max_results = 10

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        organization_id = None
        if "organization__pk" in dependent_fields:
            organization_id = dependent_fields.pop("organization__pk")
        if queryset:
            domain = get_current_domain(request)
            queryset = queryset.annotate(
                absolute_url=Concat(
                    Value(domain),
                    Value("/datasets/"),
                    "pk",
                    Value("/"),
                    output_field=_CharField(),
                )
            )
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)
        if organization_id:
            organization_datasets = queryset.filter(organization__pk=organization_id).values_list("pk", flat=True)
            if organization_datasets:
                preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(organization_datasets)])
                queryset = queryset.order_by(preserved)
        return queryset


class DatasetRelationForm(forms.ModelForm):
    organization_id = forms.IntegerField(widget=forms.HiddenInput)
    part_of = forms.ModelChoiceField(
        label=_("Duomenų rinkinys"),
        widget=PartOfWidget(attrs={"data-width": "100%", "data-minimum-input-length": 0}),
        queryset=Dataset.public.all(),
    )
    relation_type = forms.ChoiceField(label=_("Ryšio tipas"))

    class Meta:
        model = DatasetRelation
        fields = (
            "organization_id",
            "relation_type",
            "part_of",
        )

    def __init__(self, dataset, *args, **kwargs):
        self.dataset = dataset
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "dataset-relation-form"
        self.helper.layout = Layout(
            Field("organization_id"),
            Field("relation_type"),
            Field("part_of"),
            Submit("submit", _("Pridėti"), css_class="button is-primary"),
        )

        self.initial["organization_id"] = self.dataset.organization.pk

        relation_choices = [(None, "---------")]
        for rel in Relation.objects.all():
            relation_choices.append((f"{rel.pk}", rel.title))
            relation_choices.append((f"{rel.pk}_inv", rel.inversive_title))
        self.fields["relation_type"].choices = tuple(relation_choices)

    def clean_part_of(self):
        part_of = self.cleaned_data.get("part_of")
        relation = self.cleaned_data.get("relation_type")

        if relation:
            inverse = False
            if relation.endswith("_inv"):
                relation = relation.replace("_inv", "")
                inverse = True
            try:
                relation = Relation.objects.get(pk=int(relation))
            except (ValueError, ObjectDoesNotExist):
                raise ValidationError(_("Neteisinga ryšio tipo reikšmė."))

            if inverse:
                if DatasetRelation.objects.filter(relation=relation, dataset=part_of, part_of=self.dataset):
                    raise ValidationError(
                        _(f'"{relation.inversive_title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.')
                    )
            else:
                if DatasetRelation.objects.filter(relation=relation, dataset=self.dataset, part_of=part_of):
                    raise ValidationError(_(f'"{relation.title}" ryšys su šiuo duomenų rinkiniu jau egzistuoja.'))

        return part_of


class PlanChoiceField(ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.deadline:
            return mark_safe(f"<a href={obj.get_absolute_url()}>{obj.title} ({obj.deadline})</a>")
        else:
            return mark_safe(f"<a href={obj.get_absolute_url()}>{obj.title}</a>")


class DatasetPlanForm(forms.ModelForm):
    plan = PlanChoiceField(label=_("Terminas"), widget=forms.RadioSelect(), queryset=Plan.objects.all())
    form_type = CharField(widget=HiddenInput(), initial="include_form")

    class Meta:
        model = PlanDataset
        fields = (
            "plan",
            "form_type",
        )

    def __init__(self, dataset, *args, **kwargs):
        self.dataset = dataset
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "dataset-plan-form"
        self.helper.layout = Layout(
            Field("form_type"),
            Field("plan"),
            Submit("submit", _("Įtraukti"), css_class="button is-primary"),
        )

        self.fields["plan"].queryset = self.fields["plan"].queryset.filter(
            Q(deadline__isnull=True) | Q(deadline__gt=date.today())
        )

    def clean_plan(self):
        plan = self.cleaned_data.get("plan")
        if PlanDataset.objects.filter(plan=plan, dataset=self.dataset):
            raise ValidationError(_("Duomenų rinkinys jau priskirtas šiam planui."))
        return plan


class PlanForm(OrganizationPlanForm):
    form_type = CharField(widget=HiddenInput(), initial="create_form")

    class Meta:
        model = Plan
        fields = (
            "title",
            "description",
            "deadline",
            "publisher",
            "provider_title",
            "receiver",
        )

    def __init__(self, obj, organizations, user, *args, **kwargs):
        self.obj = obj
        super().__init__(organizations, user, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs["novalidate"] = ""
        self.helper.form_id = "plan-form"
        self.helper.layout = Layout(
            Field("form_type"),
            Field("organizations"),
            Field("user_id"),
            Field("title"),
            Field("description"),
            Field("deadline"),
            Field("receiver"),
            Field("publisher"),
            Field("provider_title"),
            Submit("submit", _("Įtraukti"), css_class="button is-primary"),
        )

        if len(self.organizations) == 1:
            self.initial["receiver"] = self.organizations[0]
            self.fields["receiver"].widget = HiddenInput()
        else:
            organization_ids = [org.pk for org in self.organizations]
            self.fields["receiver"].queryset = self.fields["receiver"].queryset.filter(pk__in=organization_ids)

        self.initial["title"] = self.obj.get_plan_title()
