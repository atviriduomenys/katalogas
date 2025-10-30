import os
from itertools import groupby
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.files.base import ContentFile
from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.forms import modelformset_factory, BaseFormSet
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseBase, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, FormView

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses, AGREEMENT_STATUS_DESCRIPTIONS
from vitrina.smart_contracts.forms import (
    SmartContractForm,
    SmartContractFormSetHelper,
    AgreementUploadForm,
    AgreementGeneratePdfForm,
)
from vitrina.smart_contracts.models import (
    Agreement,
    AgreementScope,
    AgreementFile,
    SmartContractTemplate,
)
from vitrina.users.models import User
from vitrina.structure.models import Metadata
from vitrina.views import FormsetView
from vitrina.smart_contracts.services import (
    get_agreements,
    can_view_agreements,
    can_create_agreements,
    can_view_agreement,
    can_upload_agreement_file,
)
from vitrina.projects.views import ProjectViewBaseMixin


class BaseProjectMixin(ProjectViewBaseMixin):
    def get_project_queryset(self):
        return Project.public.all().prefetch_related(
            Prefetch(
                "datasets",
                queryset=Dataset.public.all().order_by("organization_id"),
                to_attr="public_datasets",
            )
        )

    def get_project(self, project_id: int):
        if not hasattr(self, "_project"):
            self._project = get_object_or_404(self.get_project_queryset(), pk=project_id)
        return self._project


class BaseAgreementMixin:
    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.agreement = get_object_or_404(
            Agreement.objects.all().select_related("assigner").prefetch_related("scopes"),
            project=self.project,
            pk=self.kwargs["agreement_id"],
        )


class AgreementListView(
    LoginRequiredMixin,
    BaseProjectMixin,
    PermissionRequiredMixin,
    TemplateView,
):
    model = Agreement
    template_name = "smart_contracts/agreement_list.html"

    detail_url_name = "project-detail"
    history_url_name = "project-history"

    project: Project

    def has_permission(self) -> bool:
        return can_view_agreements(self.request.user, self.project)

    def dispatch(self, request, *args, **kwargs):
        dispatch = super().dispatch(request, *args, **kwargs)
        if not self.project.organization:
            messages.error(
                self.request,
                _("Panaudojimo atvejis registruotas fizinio asmens vardu negali turėti sutarčių."),
            )
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": self.project.pk}))
        return dispatch

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        project_agreements = get_agreements(self.request.user).filter(project=self.project)

        paginator = Paginator(project_agreements, 10)
        page_number = self.request.GET.get("page")
        page = paginator.get_page(page_number)

        context.update(
            {
                "project": self.project,
                "agreements": page.object_list,
                "agreement_status_descriptions": AGREEMENT_STATUS_DESCRIPTIONS,
                "page_obj": page,
                "paginator": paginator,
                "can_create_agreements": can_create_agreements(self.request.user, self.project),
            }
        )
        context["parent_links"].update(
            {
                None: _("Sutartys"),
            }
        )
        return context


class AgreementDetailView(
    LoginRequiredMixin,
    BaseProjectMixin,
    BaseAgreementMixin,
    PermissionRequiredMixin,
    TemplateView,
):
    model = Agreement
    template_name = "smart_contracts/agreement_detail.html"

    detail_url_name = "project-detail"
    history_url_name = "project-history"

    project: Project
    agreement: Agreement

    def has_permission(self) -> bool:
        return can_view_agreement(self.request.user, self.agreement)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "agreement": self.agreement,
                "agreement_files": self.agreement.files.all().order_by("-created_at"),
                "agreement_status_descriptions": AGREEMENT_STATUS_DESCRIPTIONS,
                "page_title": self.agreement.detail_page_title,
                "can_create_agreements": can_create_agreements(self.request.user, self.project),
                "can_upload_agreement_file": can_upload_agreement_file(self.request.user, self.agreement),
            }
        )
        context["parent_links"].update(
            {
                reverse("agreement-list", args=[self.project.pk]): _("Sutartys"),
                None: self.agreement.detail_page_title,
            }
        )
        return context


class AgreementCreateView(
    LoginRequiredMixin,
    BaseProjectMixin,
    PermissionRequiredMixin,
    FormsetView,
):
    project: Project

    model = Project
    template_name = "smart_contracts/agreement_create.html"

    def has_permission(self) -> bool:
        self.project = self.get_project(self.kwargs["pk"])
        return can_create_agreements(self.request.user, self.project)

    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not self.has_permission():
            return self.handle_no_permission()

        if not self.get_dataset_metadata_by_organization:
            messages.error(
                self.request,
                _("Šis panaudojimo atvejis jau turi egzistuojančias sutartis."),
            )
            return HttpResponseRedirect(self.get_success_url())

        if not self.project.organization:
            messages.error(
                self.request,
                _("Privatūs asmenys negali sudaryti sutarčių."),
            )
            return HttpResponseRedirect(self.get_success_url())

        return super(PermissionRequiredMixin, self).dispatch(request, *args, **kwargs)

    @cached_property
    def get_dataset_metadata_by_organization(self) -> dict[int, list[Metadata]]:
        agreement_organization_ids = Agreement.objects.filter(project=self.project).values_list(
            "assigner_id", flat=True
        )
        dataset_metadata_query = Metadata.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id__in=(d.id for d in self.project.public_datasets),
        ).exclude(
            Q(dataset__organization_id__in=agreement_organization_ids) | Q(name="") | Q(name__isnull=True),
        )

        # Assign only one metadata for each dataset, in case there are more.
        # There shouldn't be more, but DB schema allows it.
        dataset_metadata = {}
        for metadata in dataset_metadata_query:
            dataset_metadata.setdefault(metadata.dataset_id, metadata)

        sorted_dataset_metadata = sorted(dataset_metadata.values(), key=lambda m: m.dataset.organization_id)
        metadata_by_organization = {
            organization_id: list(organization_metadata)
            for organization_id, organization_metadata in groupby(
                sorted_dataset_metadata, lambda m: m.dataset.organization_id
            )
        }

        return metadata_by_organization

    def get_formset(self) -> BaseFormSet:
        formset_kwargs = self.get_formset_kwargs()
        dataset_metadata_by_organization = self.get_dataset_metadata_by_organization

        SmartContractFormset = modelformset_factory(Organization, form=SmartContractForm, extra=0)
        organization_queryset = Organization.objects.filter(pk__in=dataset_metadata_by_organization.keys()).order_by(
            "pk"
        )
        formset = SmartContractFormset(
            **formset_kwargs,
            queryset=organization_queryset,
            form_kwargs={"dataset_metadata_by_organization": dataset_metadata_by_organization},
        )

        return formset

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "formset_helper": SmartContractFormSetHelper(),
                "current_title": _("Generuoti sutartis"),
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("project-list"): _("Panaudojimo atvejai"),
                    reverse("project-detail", args=[self.project.pk]): self.project,
                    None: _("Generuoti sutartis"),
                },
            }
        )

        return context

    def get_success_url(self) -> str:
        return reverse("agreement-list", args=[self.project.pk])

    @transaction.atomic
    def formset_valid(self, formset: BaseFormSet) -> HttpResponse:
        current_user: User = self.request.user
        for form in formset:
            agreement = Agreement.objects.create(
                project=self.project,
                assigner=form.instance,
                status=AgreementStatuses.CREATED,
                created_by=current_user,
                assignee=self.project.organization,
            )
            agreement_scopes = []
            for scope in form.cleaned_data["scopes"]:
                resource, action = scope.rsplit("/:", 1)
                agreement_scopes.append(
                    AgreementScope(
                        agreement=agreement,
                        scope=scope,
                        resource=resource,
                        action=action,
                    )
                )
            AgreementScope.objects.bulk_create(agreement_scopes)

        messages.success(self.request, _("Sutartys sėkmingai sugeneruotos"))
        return super().formset_valid(formset)

    def formset_invalid(self, formset: BaseFormSet) -> HttpResponse:
        messages.error(self.request, _("Sutarčių generavime kilo klaidų"))
        return super().formset_invalid(formset)


class AgreementGeneratePdf(
    LoginRequiredMixin,
    BaseProjectMixin,
    BaseAgreementMixin,
    PermissionRequiredMixin,
    FormView,
):
    form_class = AgreementGeneratePdfForm
    template_name = "base_form.html"
    detail_url_name = "project-detail"
    history_url_name = "project-history"

    def setup(self, request, *args, **kwargs):
        self.object = self.get_project(kwargs["pk"])
        return super().setup(request, *args, **kwargs)

    def has_permission(self) -> bool:
        return can_create_agreements(self.request.user, self.object)

    def get_success_url(self) -> str:
        return reverse("agreement-detail", args=[self.object.pk, self.agreement.pk])

    @transaction.atomic
    def form_valid(self, form: AgreementGeneratePdfForm) -> HttpResponse:
        if self.agreement.status != AgreementStatuses.CREATED:
            error_msg = _(
                "Sutarties dokumentas gali būti generuojamas sutarčiai su "
                "būsena {accepted_status}. Dabartinė būsena: {current_status}"
            ).format(
                accepted_status=AgreementStatuses.CREATED,
                current_status=self.agreement.status,
            )
            messages.error(self.request, error_msg)
            return HttpResponseRedirect(self.get_success_url())

        contract_template: SmartContractTemplate = form.cleaned_data["template"]
        self.agreement.status = AgreementStatuses.FORMED
        self.agreement.other_assigner_legislations = form.cleaned_data["other_assigner_legislations"]
        self.agreement.other_assignee_legislations = form.cleaned_data["other_assignee_legislations"]
        self.agreement.payment_terms = form.cleaned_data["payment_terms"]
        self.agreement.save()
        self.agreement.generate_contract_pdf_file(template=contract_template)
        name_without_ext, ext = os.path.splitext(os.path.basename(contract_template.file.name))

        copy_filename = f"{name_without_ext}_copy{ext}"
        with contract_template.file.open() as f:
            self.agreement.files.create(
                file=ContentFile(content=f.read(), name=copy_filename),
                is_template=True,
                file_name=copy_filename,
            )

        messages.success(self.request, _("Sutarties dokumentas sukurtas"))
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["agreement"] = self.agreement
        return kwargs

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "tabs": "vitrina/projects/tabs.html",
                "current_title": _("Generuoti sutarties dokumentą"),
            }
        )
        context["parent_links"].update(
            {
                reverse("agreement-list", args=[self.object.pk]): _("Sutartys"),
                reverse("agreement-detail", args=[self.object.pk, self.agreement.pk]): self.agreement.detail_page_title,
                None: _("Generuoti sutarties dokumentą"),
            }
        )

        return context


class AgreementUploadSignedFile(
    LoginRequiredMixin,
    BaseProjectMixin,
    BaseAgreementMixin,
    PermissionRequiredMixin,
    FormView,
):
    form_class = AgreementUploadForm
    template_name = "base_form.html"

    def setup(self, request, *args, **kwargs):
        self.object = self.get_project(kwargs["pk"])
        return super().setup(request, *args, **kwargs)

    def has_permission(self) -> bool:
        return can_upload_agreement_file(self.request.user, self.agreement)

    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        accepted_statuses = (AgreementStatuses.FORMED, AgreementStatuses.INITIATED)
        error_msg = ""
        if self.agreement.status not in accepted_statuses:
            error_msg = _(
                "Sutarties dokumentas gali būti generuojamas sutarčiai su "
                "būsenomis {accepted_statuses}. Dabartinė būsena: {current_status}"
            ).format(
                accepted_statuses=", ".join(accepted_statuses),
                current_status=self.agreement.status,
            )
        if (
            self.agreement.status == AgreementStatuses.FORMED
            and request.user.viisp_organization != self.agreement.assignee
        ):
            error_msg = _(
                "Sutartį pasirašyti duomenų teikėjo vardu galėsite tik po to kai ją pasirašys duomenų gavėjas."
            )
        elif (
            self.agreement.status == AgreementStatuses.INITIATED
            and request.user.viisp_organization != self.agreement.assigner
        ):
            error_msg = _("Gavėjo vardu sutartis jau pasirašyta. Laukiama sutarties pasirašymo iš teikėjo pusės.")
        if error_msg:
            messages.error(request, error_msg)
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        agreement_details_title = _("Sutartis: {organization}").format(organization=self.agreement.assigner)
        page_title = (
            _("Įkelti gavėjo pasirašytą dokumentą")
            if self.agreement.status == AgreementStatuses.FORMED
            else _("Įkelti teikėjo pasirašytą dokumentą")
        )
        context["current_title"] = page_title
        context["tabs"] = "vitrina/projects/tabs.html"
        context["parent_links"].update(
            {
                reverse("agreement-list", args=[self.object.pk]): _("Sutartys"),
                reverse("agreement-detail", args=[self.object.pk, self.agreement.pk]): agreement_details_title,
                None: page_title,
            }
        )

        return context

    def get_success_url(self) -> str:
        return reverse("agreement-detail", args=[self.object.pk, self.agreement.pk])

    def form_valid(self, form: AgreementUploadForm) -> HttpResponse:
        if self.agreement.status == AgreementStatuses.FORMED:
            self.agreement.status = AgreementStatuses.INITIATED
        else:
            self.agreement.status = AgreementStatuses.SIGNED
            self.agreement.is_agent_sync_enabled = True
        self.agreement.save()

        AgreementFile.objects.create(
            agreement=self.agreement,
            file_name=form.cleaned_data["file"].name,
            file=form.cleaned_data["file"],
        )

        messages.success(self.request, _("Sutarties dokumentas įkeltas sėkmingai"))
        return HttpResponseRedirect(self.get_success_url())
