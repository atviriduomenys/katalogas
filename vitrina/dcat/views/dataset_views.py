import json
import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseRedirect, HttpResponseBase
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import get_language
from django.views import View
from parler.views import TranslatableCreateView, LanguageChoiceMixin, TranslatableUpdateView
from django.utils.translation import gettext_lazy as _

from vitrina.catalogs.models import Catalog
from vitrina.classifiers.models import Frequency
from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.datasets.view_helpers import (
    create_tasks_and_notify_subscribers_about_dataset_creation,
    create_dataset_representative_and_attribution,
    create_tasks_and_notify_subscribers_about_dataset_update,
    save_dataset_creator,
)
from vitrina.dcat.view_helpers import (
    save_dataset_relations,
    save_dataset_attribution,
    save_dataset_qualified_relations,
)
from vitrina.dcat.forms.dataset_forms import (
    InformationSystemResourceForm,
    BaseResourceForm,
    ServiceResourceForm,
    DatasetResourceForm,
    InformationSystemUpdateForm,
    ServiceUpdateForm,
    DatasetUpdateForm,
    InformationSystemRelationshipForm,
    ServiceRelationshipForm,
    DatasetRelationshipForm,
)
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

DCAT_SUBCLASS_UPDATE_FORM_MAP = {
    DCATResourceSubclass.INFORMATION_SYSTEM: InformationSystemUpdateForm,
    DCATResourceSubclass.SERVICE: ServiceUpdateForm,
    DCATResourceSubclass.DATASET: DatasetUpdateForm,
}

DCAT_SUBCLASS_RELATIONSHIP_FORM_MAP = {
    DCATResourceSubclass.INFORMATION_SYSTEM: InformationSystemRelationshipForm,
    DCATResourceSubclass.SERVICE: ServiceRelationshipForm,
    DCATResourceSubclass.DATASET: DatasetRelationshipForm,
}

# Maps DCAT subclass name → wizard tree node-key prefix (mirrors WIZARD_NODE_* in orgs/views.py)
_WIZARD_NODE_KEY_PREFIX = {
    DCATResourceSubclass.INFORMATION_SYSTEM: "is",
    DCATResourceSubclass.SERVICE: "service",
    DCATResourceSubclass.DATASET: "dataset",
}

# Lithuanian grammatical gender for the word "new" per subclass
DCAT_SUBCLASS_NEW_WORD = {
    DCATResourceSubclass.INFORMATION_SYSTEM: _("Nauja"),
    DCATResourceSubclass.SERVICE: _("Nauja"),
    DCATResourceSubclass.DATASET: _("Naujas"),
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

    @cached_property
    def dataset_parent(self) -> Dataset | None:
        if parent_id := self.kwargs.get("parent_id"):
            return get_object_or_404(Dataset.objects.select_related("organization"), pk=parent_id)
        return None

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.CREATE_WIZARD, Dataset, self.organization)

    def _is_wizard_request(self) -> bool:
        return bool(self.request.headers.get("X-Wizard-Request"))

    def get_template_names(self) -> list[str]:
        if self._is_wizard_request():
            return ["vitrina/dcat/_wizard_dataset_create_fragment.html"]
        return super().get_template_names()

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
                "new_word": DCAT_SUBCLASS_NEW_WORD.get(self.subclass.name, _("Naujas")),
                "current_step": 2,
                "current_percentage": 100,
                "button": _("Sukurti"),
            }
        )
        if self._is_wizard_request():
            parent_id = self.kwargs.get("parent_id")
            if parent_id:
                context["wizard_create_post_url"] = reverse(
                    "dcat-dataset-create-with-parent",
                    kwargs={
                        "organization_id": self.organization.pk,
                        "parent_id": parent_id,
                        "subclass_uuid": self.subclass.pk,
                    },
                )
            else:
                context["wizard_create_post_url"] = reverse(
                    "dcat-dataset-create",
                    kwargs={
                        "organization_id": self.organization.pk,
                        "subclass_uuid": self.subclass.pk,
                    },
                )
        return context

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["url_parent"] = self.dataset_parent

        return kwargs

    def form_valid(self, form: BaseResourceForm) -> HttpResponseBase:
        with transaction.atomic():
            language = self.request.GET.get("language", get_language())

            self.object = form.save(commit=False)
            self.object.set_current_language(language)

            self.object.subclass = self.subclass
            self.object.is_public = False
            self.object.catalog = self.catalog

            # Set treebeard path fields directly, mirroring add_self_as_root().
            # Dataset.node_order_by forces sorted-sibling insertion which fails on
            # dense path sequences — bypassing add_root/add_child avoids this entirely.
            parent: Dataset | None = form.cleaned_data.get("parent", None)
            if parent:
                last_child = parent.get_last_child()
                self.object.path = (
                    last_child._inc_path() if last_child else Dataset._get_path(parent.path, parent.depth + 1, 1)
                )
                self.object.depth = parent.depth + 1
            else:
                last_root = Dataset.get_last_root_node()
                self.object.path = last_root._inc_path() if last_root else Dataset._get_path(None, 1, 1)
                self.object.depth = 1
            self.object.numchild = 0

            if self.subclass.name == DCATResourceSubclass.INFORMATION_SYSTEM or self._is_wizard_request():
                self.object.organization = self.organization

            if self.subclass.name == DCATResourceSubclass.INFORMATION_SYSTEM:
                self.object.access_rights = Dataset.CONFIDENTIAL
                self.object.frequency = Frequency.objects.filter(code=Frequency.CODE_UNKNOWN).first()

            if self.subclass.name == DCATResourceSubclass.SERVICE:
                self.object.service = True

            self.object.save()

            if parent:
                Dataset.objects.filter(pk=parent.pk).update(numchild=F("numchild") + 1)

            if self.subclass.name == DCATResourceSubclass.INFORMATION_SYSTEM:
                if identifier := form.cleaned_data.get("identifier"):
                    agency = get_object_or_404(Agency, code=Agency.RISR_CODE)
                    Identifier.objects.create(
                        resource=self.object,
                        notation=identifier,
                        scheme_agency=agency,
                        identifier_type=Identifier.IdentifierType.OTHER,
                    )
            tags = form.cleaned_data.get("tags")
            self.object.tags.set(tags)
            self.object.information_system_publishers.set(form.cleaned_data.get("information_system_publishers") or [])

            dataset_name = form.get_dataset_name()
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

            save_dataset_qualified_relations(self.object, form)
            save_dataset_creator(self.request, self.object, form)

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

        self.object.category.set(form.cleaned_data.get("category") or [])

        messages.success(
            self.request, _("Duomenų išteklius sukurtas sėkmingai. Kodinis pavadinimas: {0}").format(dataset_name)
        )

        if self._is_wizard_request():
            self.object.set_current_language(get_language())
            update_form = DCAT_SUBCLASS_UPDATE_FORM_MAP[self.subclass.name](
                self.organization, None, instance=self.object
            )
            update_form.helper.form_tag = False
            rel_form_class = DCAT_SUBCLASS_RELATIONSHIP_FORM_MAP.get(self.subclass.name)
            context = {
                "form": update_form,
                "relationship_form": rel_form_class(self.object) if rel_form_class else None,
                "dataset": self.object,
                "organization": self.organization,
                "form_title": self.subclass.translated_title,
                "information_title": self.subclass.translated_title,
            }
            response = render(self.request, "vitrina/dcat/_wizard_dataset_fragment.html", context)
            node_prefix = _WIZARD_NODE_KEY_PREFIX.get(self.subclass.name, "dataset")
            response["HX-Trigger"] = json.dumps(
                {
                    "treeRefresh": None,
                    "wizardnodecreated": {"nodeKey": f"{node_prefix}:{self.object.pk}"},
                }
            )
            return response

        return HttpResponseRedirect(
            reverse(
                "dcat-dataset-update",
                kwargs={
                    "dataset_id": self.object.pk,
                    "organization_id": self.object.organization_id,
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

    @cached_property
    def dataset_parent(self) -> Dataset | None:
        if parent_id := self.kwargs.get("parent_id"):
            return get_object_or_404(Dataset.objects.select_related("organization"), pk=parent_id)
        return None

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE_WIZARD, self.get_object())

    def _is_wizard_request(self) -> bool:
        return bool(self.request.headers.get("X-Wizard-Request"))

    def get_template_names(self) -> list[str]:
        if self._is_wizard_request():
            return ["vitrina/dcat/_wizard_dataset_fragment.html"]
        return super().get_template_names()

    def _wizard_notice(self, message: str) -> HttpResponseBase:
        from django.http import HttpResponse

        return HttpResponse(f'<div class="notification is-warning is-light">{message}</div>')

    def dispatch(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        obj = self.get_object()
        if obj.is_public:
            if self._is_wizard_request():
                return self._wizard_notice(str(_("Vedlio negalima naudoti su atvirais duomenų ištekliais.")))
            messages.warning(request, _("Vedlio negalima naudoti su atvirais duomenų ištekliais"))
            return HttpResponseRedirect(reverse("organization-detail", kwargs={"pk": self.organization.pk}))
        if obj.subclass.name not in (
            DCATResourceSubclass.INFORMATION_SYSTEM,
            DCATResourceSubclass.SERVICE,
            DCATResourceSubclass.DATASET,
        ):
            if self._is_wizard_request():
                return self._wizard_notice(str(_("Vedlio negalima naudoti su šiuo duomenų ištekliaus poklasiu.")))
            messages.warning(request, _("Vedlio negalima naudoti su šiuo duomenų ištekliaus poklasiu"))
            return HttpResponseRedirect(reverse("organization-detail", kwargs={"pk": self.organization.pk}))
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self) -> BaseResourceForm:
        if (form_class := DCAT_SUBCLASS_UPDATE_FORM_MAP.get(self.subclass.name)) is None:
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
        rel_form_class = DCAT_SUBCLASS_RELATIONSHIP_FORM_MAP.get(self.subclass.name)
        context["relationship_form"] = rel_form_class(self.get_object()) if rel_form_class else None
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
        kwargs["url_parent"] = self.dataset_parent

        return kwargs

    def form_valid(self, form: BaseResourceForm) -> HttpResponseBase:
        self.object = form.save(commit=False)
        tags = form.cleaned_data["tags"]
        self.object.tags.set(tags)
        self.object.information_system_publishers.set(form.cleaned_data.get("information_system_publishers") or [])

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

        save_dataset_qualified_relations(self.object, form)

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

        if "category" in form.changed_data:
            self.object.category.set(form.cleaned_data.get("category") or [])

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
        dataset_name = form.get_dataset_name()
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
            self.object.refresh_from_db()  # Refresh needed after moving tree nodes

        save_dataset_relations(self.request, self.object, form)
        save_dataset_attribution(self.request, self.object, form)
        save_dataset_creator(self.request, self.object, form)

        rel_form_class = DCAT_SUBCLASS_RELATIONSHIP_FORM_MAP.get(self.subclass.name)
        if rel_form_class:
            rel_form = rel_form_class(self.object, data=self.request.POST)
            if rel_form.is_valid():
                save_dataset_relations(self.request, self.object, rel_form)
                save_dataset_attribution(self.request, self.object, rel_form)

        messages.success(
            self.request, _("Duomenų išteklius atnaujintas sėkmingai. Kodinis pavadinimas: {0}").format(dataset_name)
        )

        if self._is_wizard_request():
            self.object.set_current_language(get_language())
            fresh_form = DCAT_SUBCLASS_UPDATE_FORM_MAP[self.subclass.name](
                self.organization, None, instance=self.object
            )
            response = render(
                self.request,
                "vitrina/dcat/_wizard_dataset_fragment.html",
                self.get_context_data(form=fresh_form),
            )
            response["HX-Trigger"] = "treeRefresh"
            return response

        return HttpResponseRedirect(
            reverse(
                "dcat-dataset-update",
                kwargs={
                    "dataset_id": self.object.pk,
                    "organization_id": self.object.organization_id,
                },
            )
        )


class DcatDatasetRelationshipUpdateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    @cached_property
    def organization(self) -> Organization:
        return get_object_or_404(Organization, pk=self.kwargs["organization_id"])

    @cached_property
    def dataset(self) -> Dataset:
        return get_object_or_404(
            Dataset.objects.select_related("subclass"),
            pk=self.kwargs["dataset_id"],
            organization=self.organization,
        )

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE_WIZARD, self.dataset)

    def post(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        form_class = DCAT_SUBCLASS_RELATIONSHIP_FORM_MAP.get(self.dataset.subclass.name)
        if not form_class:
            return self._render_fragment()

        relationship_form = form_class(self.dataset, data=request.POST)
        if relationship_form.is_valid():
            save_dataset_relations(request, self.dataset, relationship_form)
            save_dataset_attribution(request, self.dataset, relationship_form)
            messages.success(request, _("Ryšiai atnaujinti sėkmingai"))
            relationship_form = form_class(self.dataset)

        return self._render_fragment(relationship_form=relationship_form)

    def _render_fragment(self, relationship_form=None) -> HttpResponseBase:
        main_form_class = DCAT_SUBCLASS_UPDATE_FORM_MAP.get(self.dataset.subclass.name)
        main_form = main_form_class(self.organization, None, instance=self.dataset) if main_form_class else None
        if main_form and hasattr(main_form, "helper"):
            main_form.helper.form_tag = False

        if relationship_form is None:
            form_class = DCAT_SUBCLASS_RELATIONSHIP_FORM_MAP.get(self.dataset.subclass.name)
            relationship_form = form_class(self.dataset) if form_class else None

        context = {
            "form": main_form,
            "relationship_form": relationship_form,
            "dataset": self.dataset,
            "organization": self.organization,
            "form_title": self.dataset.subclass.translated_title,
            "information_title": self.dataset.subclass.translated_title,
        }
        response = render(self.request, "vitrina/dcat/_wizard_dataset_fragment.html", context)
        response["HX-Trigger"] = "treeRefresh"
        return response
