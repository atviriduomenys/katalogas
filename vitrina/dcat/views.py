import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.http import HttpResponseRedirect, HttpResponseBase
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import get_language
from parler.views import TranslatableCreateView, LanguageChoiceMixin, TranslatableUpdateView
from django.utils.translation import gettext_lazy as _

from vitrina.catalogs.models import Catalog
from vitrina.classifiers.models import Frequency
from vitrina.datasets.helpers import generate_unique_dataset_name
from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.datasets.view_helpers import (
    create_tasks_and_notify_subscribers_about_dataset_creation,
    create_dataset_representative_and_attribution,
    create_tasks_and_notify_subscribers_about_dataset_update,
)
from vitrina.dcat.forms import InformationSystemResourceForm, BaseResourceForm, ServiceResourceForm, DatasetResourceForm
from vitrina.identifiers.models import Agency, Identifier
from vitrina.orgs.models import Organization
from vitrina.orgs.services import Action, has_perm
from vitrina.structure import VersionStatus
from vitrina.structure.models import Version as _Version, Metadata
from vitrina.structure.services import get_model_name


DCAT_SUBCLASS_FORM_MAP = {
    DCATResourceSubclass.INFORMATION_SYSTEM: InformationSystemResourceForm,
    DCATResourceSubclass.SERVICE: ServiceResourceForm,
    DCATResourceSubclass.DATASET: DatasetResourceForm,
}


class DcatDatasetCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    TranslatableCreateView,
    LanguageChoiceMixin,
):
    model = Dataset
    template_name = "vitrina/dcat/dataset_form.html"
    context_object_name = "dataset"

    @cached_property
    def organization(self) -> Organization:
        return get_object_or_404(Organization, pk=self.kwargs.get("organization_id"))

    @cached_property
    def subclass(self) -> DCATResourceSubclass:
        return get_object_or_404(DCATResourceSubclass, pk=self.kwargs.get("subclass_uuid"))

    @cached_property
    def catalog(self) -> Catalog:
        isris_catalog, created = Catalog.objects.get_or_create(
            identifier=Catalog.IDENTIFIER_ISRIS,
            defaults={
                "title": "ISRIS",
                "description": "ISRIS - Informacinių sistemų ir Registrų katalogas",
                "version": "1",
            },
        )
        return isris_catalog

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.CREATE_WIZARD, Dataset, self.organization)

    def dispatch(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        is_valid_subclass = self.subclass.name in [
            DCATResourceSubclass.INFORMATION_SYSTEM,
            DCATResourceSubclass.SERVICE,
            DCATResourceSubclass.DATASET,
        ]

        if not is_valid_subclass:
            messages.error(request, _("Vedlio negalima naudoti su šiuo duomenų ištekliaus poklasiu"))
            return HttpResponseRedirect(reverse("organization-detail", kwargs={"pk": self.organization.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self) -> BaseResourceForm:
        if (form_class := DCAT_SUBCLASS_FORM_MAP.get(self.subclass.name)) is None:
            raise ImproperlyConfigured(_("Nurodytas duomenų ištekliaus poklasis neturi formos."))

        return form_class

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "organization": self.organization,
                "organization_id": self.organization.pk,
                "current_title": _("Pridėti duomenų išteklių"),
                "form_title": self.subclass.translated_title,
                "information_title": self.subclass.translated_title,
                "information_description": self.subclass.translated_description,
                "current_step": 2,
                "current_percentage": 100,
                "button": _("Sukurti"),
            }
        )
        return context

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["parent_dataset_id"] = self.kwargs.get("parent_id")

        return kwargs

    def form_valid(self, form: BaseResourceForm) -> HttpResponseBase:
        language = self.request.GET.get("language", get_language())

        self.object = form.save(commit=False)
        self.object.set_current_language(language)
        self.object.organization = self.organization
        self.object.subclass = self.subclass
        self.object.is_public = False
        self.object.catalog = self.catalog

        parent: Dataset | None = form.cleaned_data.get("parent", None)
        if parent:
            parent.add_child(instance=self.object)
        else:
            Dataset.add_root(instance=self.object)

        if self.subclass.name == DCATResourceSubclass.INFORMATION_SYSTEM:
            self.object.access_rights = Dataset.CONFIDENTIAL
            self.object.frequency = Frequency.objects.filter(code=Frequency.CODE_UNKNOWN).first()
            if identifier := form.cleaned_data.get("identifier"):
                agency = get_object_or_404(Agency, code=Agency.RISR_CODE)
                Identifier.objects.create(
                    resource=self.object,
                    notation=identifier,
                    scheme_agency=agency,
                    identifier_type=Identifier.IdentifierType.OTHER,
                )

        if self.subclass.name == DCATResourceSubclass.SERVICE:
            self.object.service = True

        self.object.save()
        tags = form.cleaned_data.get("tags")
        self.object.tags.set(tags)

        dataset_name = form.cleaned_data.get("name", "") or generate_unique_dataset_name(
            self.object.organization, self.object
        )
        draft_metadata_version = _Version.objects.create(
            dataset=self.object,
            version=1,
            status=VersionStatus.DRAFT,
        )
        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=self.object,
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.pk,
            name=dataset_name,
            title=self.object.title,
            description=self.object.description,
            prepare_ast={},
            version=1,
            metadata_version=draft_metadata_version,
        )

        create_tasks_and_notify_subscribers_about_dataset_creation(self.request, self.object)
        create_dataset_representative_and_attribution(self.object)

        if applicable_legislation_urls := form.cleaned_data.get("applicable_legislation"):
            self.object.update_applicable_legislation(applicable_legislation_urls)

        if documentation_urls := form.cleaned_data.get("documentation"):
            self.object.update_documentation(documentation_urls)

        if "service_type" in form.changed_data:
            self.object.service_type.set(form.cleaned_data["service_type"])

        if "follows" in form.changed_data:
            self.object.follows.set(form.cleaned_data.get("follows"))

        if "service_quality" in form.changed_data:
            self.object.update_service_quality(form.cleaned_data.get("service_quality"))

        if "languages" in form.changed_data:
            self.object.languages.set(form.cleaned_data.get("languages"))

        if "provenance" in form.changed_data:
            self.object.provenance.set(form.cleaned_data.get("provenance"))

        if "was_generated_by" in form.changed_data:
            self.object.was_generated_by.set(form.cleaned_data.get("was_generated_by"))

        messages.success(self.request, _("Duomenų išteklius sukurtas sėkmingai"))

        return HttpResponseRedirect(
            reverse(
                "dcat-dataset-update",
                kwargs={
                    "dataset_id": self.object.pk,
                    "organization_id": self.organization.pk,
                },
            )
        )


class DcatDatasetUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    TranslatableUpdateView,
    LanguageChoiceMixin,
):
    model = Dataset
    template_name = "vitrina/dcat/dataset_form.html"
    context_object_name = "dataset"
    pk_url_kwarg = "dataset_id"

    @cached_property
    def organization(self) -> Organization:
        return get_object_or_404(Organization, pk=self.kwargs.get("organization_id"))

    @cached_property
    def subclass(self) -> DCATResourceSubclass:
        return self.get_object().subclass

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE_WIZARD, self.get_object())

    def dispatch(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        obj = self.get_object()
        if obj.is_public:
            messages.warning(request, _("Vedlio negalima naudoti su atvirais duomenų ištekliais"))
            return HttpResponseRedirect(reverse("organization-detail", kwargs={"pk": self.organization.pk}))
        if obj.subclass.name not in (
            DCATResourceSubclass.INFORMATION_SYSTEM,
            DCATResourceSubclass.SERVICE,
            DCATResourceSubclass.DATASET,
        ):
            messages.warning(request, _("Vedlio negalima naudoti su šiuo duomenų ištekliaus poklasiu"))
            return HttpResponseRedirect(reverse("organization-detail", kwargs={"pk": self.organization.pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self) -> BaseResourceForm:
        if (form_class := DCAT_SUBCLASS_FORM_MAP.get(self.subclass.name)) is None:
            raise ImproperlyConfigured(_("Nurodytas duomenų ištekliaus poklasis neturi formos."))

        return form_class

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "organization": self.organization,
                "organization_id": self.organization.pk,
                "current_title": _("Duomenų ištekliaus redagavimas"),
                "form_title": self.subclass.translated_title,
                "information_title": self.subclass.translated_title,
                "information_description": self.subclass.translated_description,
                "current_step": 2,
                "current_percentage": 100,
                "button": _("Redaguoti"),
            }
        )
        return context

    def get_queryset(self) -> QuerySet[Dataset]:
        return super().get_queryset().filter(organization=self.organization).select_related("organization", "subclass")

    def get_object(self, queryset: QuerySet[Dataset] | None = None) -> Dataset:
        obj = super().get_object(queryset)
        lang = self.request.GET.get("language", get_language())
        obj.set_current_language(lang)

        return obj

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["parent_dataset_id"] = self.kwargs.get("parent_id")

        return kwargs

    def form_valid(self, form: BaseResourceForm) -> HttpResponseBase:
        self.object = form.save(commit=False)
        tags = form.cleaned_data["tags"]
        self.object.tags.set(tags)

        if "endpoint_url" in form.changed_data:
            if self.object.datasetdistribution_set.exists() or (self.object.service and self.object.endpoint_url):
                self.object.status = Dataset.HAS_DATA
            elif self.object.plandataset_set.exists():
                self.object.status = Dataset.PLANNED
            else:
                self.object.status = Dataset.INVENTORED
        elif not self.object.is_public and self.object.published:
            self.object.published = None
            self.object.status = Dataset.UNASSIGNED

        if self.object.subclass.name == DCATResourceSubclass.INFORMATION_SYSTEM and (
            identifier := form.cleaned_data.get("identifier")
        ):
            agency = get_object_or_404(Agency, code=Agency.RISR_CODE)
            Identifier.objects.update_or_create(
                resource=self.object,
                scheme_agency=agency,
                defaults={
                    "notation": identifier,
                    "identifier_type": Identifier.IdentifierType.OTHER,
                    "resource": self.object,
                    "scheme_agency": agency,
                },
            )
        if "applicable_legislation" in form.changed_data:
            self.object.update_applicable_legislation(form.cleaned_data.get("applicable_legislation"))

        if "documentation" in form.changed_data:
            self.object.update_documentation(form.cleaned_data.get("documentation"))

        if "service_type" in form.changed_data:
            self.object.service_type.set(form.cleaned_data["service_type"])

        if "follows" in form.changed_data:
            self.object.follows.set(form.cleaned_data.get("follows"))

        if "service_quality" in form.changed_data:
            self.object.update_service_quality(form.cleaned_data.get("service_quality"))

        if "languages" in form.changed_data:
            self.object.languages.set(form.cleaned_data.get("languages"))

        if "provenance" in form.changed_data:
            self.object.provenance.set(form.cleaned_data.get("provenance"))

        if "was_generated_by" in form.changed_data:
            self.object.was_generated_by.set(form.cleaned_data.get("was_generated_by"))

        self.object.save()

        if metadata := self.object.metadata.first():
            metadata.title = self.object.title
            metadata.description = self.object.description
            metadata.save()
        else:
            metadata = Metadata.objects.create(
                uuid=str(uuid.uuid4()),
                dataset=self.object,
                content_type=ContentType.objects.get_for_model(self.object),
                object_id=self.object.pk,
                title=self.object.title,
                description=self.object.description,
                prepare_ast={},
                version=1,
            )
        dataset_name = form.cleaned_data.get("name", "") or generate_unique_dataset_name(
            self.object.organization, self.object
        )
        if not metadata.name or metadata.name != dataset_name:
            metadata.name = dataset_name
            metadata.draft = True
            metadata.save()

            # Update model names
            for model in self.object.model_set.all():
                if model_meta := model.metadata.first():
                    model_meta.name = get_model_name(self.object, model.name)
                    model_meta.save()

        create_tasks_and_notify_subscribers_about_dataset_update(self.request, self.object)
        self.object.save()

        selected_parent = form.cleaned_data.get("parent")
        if self.object.get_parent() != selected_parent:
            if not selected_parent:
                self.object.add_self_as_root()
            else:
                self.object.move(selected_parent, "sorted-child")

        messages.success(self.request, _("Duomenų išteklius atnaujintas sėkmingai"))

        return HttpResponseRedirect(
            reverse(
                "dcat-dataset-update",
                kwargs={
                    "dataset_id": self.object.pk,
                    "organization_id": self.organization.pk,
                },
            )
        )
