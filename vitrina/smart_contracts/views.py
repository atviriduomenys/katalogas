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
from vitrina.orgs.services import has_perm, Action
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
from vitrina.views import FormsetView, HistoryMixin


class BaseProjectMixin:
    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.object = get_object_or_404(
            Project.public.all().prefetch_related(
                Prefetch(
                    "datasets",
                    queryset=Dataset.public.all().order_by("organization_id"),
                    to_attr="public_datasets",
                )
            ),
            pk=kwargs["pk"],
        )

        return super().dispatch(request, *args, **kwargs)


class BaseAgreementMixin:
    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.agreement = get_object_or_404(
            Agreement.objects.all().select_related("assigner").prefetch_related("scopes"),
            project=self.object,
            pk=kwargs["agreement_id"],
        )

        return super().dispatch(request, *args, **kwargs)


class AgreementListView(
    LoginRequiredMixin,
    BaseProjectMixin,
    PermissionRequiredMixin,
    HistoryMixin,
    TemplateView,
):
    model = Agreement
    template_name = "smart_contracts/agreement_list.html"

    detail_url_name = "project-detail"
    history_url_name = "project-history"

    object: Project

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, self.object)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        project_agreements = Agreement.objects.filter(
            project=self.object,
        ).order_by("-created_at")

        paginator = Paginator(project_agreements, 10)
        page_number = self.request.GET.get("page")
        page = paginator.get_page(page_number)

        context.update(
            {
                "project": self.object,
                "agreements": page.object_list,
                "agreement_status_descriptions": AGREEMENT_STATUS_DESCRIPTIONS,
                "page_obj": page,
                "paginator": paginator,
                "can_update_project": has_perm(self.request.user, Action.UPDATE, self.object),
                "can_view_agreements": has_perm(self.request.user, Action.VIEW, Agreement, self.object),
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("project-list"): _("Panaudojimo atvejai"),
                    reverse("project-detail", args=[self.object.pk]): self.object,
                    None: _("Sutartys"),
                },
            }
        )

        return context


class AgreementDetailView(
    LoginRequiredMixin,
    BaseProjectMixin,
    BaseAgreementMixin,
    PermissionRequiredMixin,
    HistoryMixin,
    TemplateView,
):
    model = Agreement
    template_name = "smart_contracts/agreement_detail.html"

    detail_url_name = "project-detail"
    history_url_name = "project-history"

    object: Project
    agreement: Agreement

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.VIEW, self.agreement)

    def get_page_tite(self) -> str:
        return _("Sutartis: {organization}").format(organization=self.agreement.assigner)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        page_title = self.get_page_tite()

        context.update(
            {
                "project": self.object,
                "agreement": self.agreement,
                "agreement_files": self.agreement.files.all().order_by("-created_at"),
                "agreement_status_descriptions": AGREEMENT_STATUS_DESCRIPTIONS,
                "page_title": page_title,
                "can_update_project": has_perm(self.request.user, Action.UPDATE, self.object),
                "can_view_agreements": has_perm(self.request.user, Action.VIEW, Agreement, self.object),
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("project-list"): _("Panaudojimo atvejai"),
                    reverse("project-detail", args=[self.object.pk]): self.object,
                    reverse("agreement-list", args=[self.object.pk]): _("Sutartys"),
                    None: page_title,
                },
            }
        )

        return context


class AgreementCreateView(
    LoginRequiredMixin,
    BaseProjectMixin,
    PermissionRequiredMixin,
    FormsetView,
):
    object: Project

    model = Project
    template_name = "smart_contracts/agreement_create.html"

    def has_permission(self) -> bool:
        return getattr(self.request.user, "organization_id", None) and (
            has_perm(self.request.user, Action.UPDATE, self.object) or self.request.user == self.object.user
        )

    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        dispatch = super().dispatch(request, *args, **kwargs)
        if not self.get_dataset_metadata_by_organization:
            messages.error(
                self.request,
                _("Šis panaudojimo atvejis jau turi egzistuojančias sutartis."),
            )
            return HttpResponseRedirect(self.get_success_url())

        return dispatch

    @cached_property
    def get_dataset_metadata_by_organization(self) -> dict[int, list[Metadata]]:
        agreement_organization_ids = Agreement.objects.filter(project=self.object).values_list("assigner_id", flat=True)
        dataset_metadata_query = Metadata.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id__in=(d.id for d in self.object.public_datasets),
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
                "project": self.object,
                "formset_helper": SmartContractFormSetHelper(),
                "current_title": _("Generuoti sutartis"),
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("project-list"): _("Panaudojimo atvejai"),
                    reverse("project-detail", args=[self.object.pk]): self.object,
                    None: _("Generuoti sutartis"),
                },
            }
        )

        return context

    def get_success_url(self) -> str:
        return reverse("agreement-list", args=[self.object.pk])

    @transaction.atomic
    def formset_valid(self, formset: BaseFormSet) -> HttpResponse:
        current_user: User = self.request.user
        for form in formset:
            agreement = Agreement.objects.create(
                project=self.object,
                assigner=form.instance,
                status=AgreementStatuses.CREATED,
                created_by=current_user,
                assignee=current_user.organization,
            )
            agreement_scopes = []
            for scope in form.cleaned_data["scopes"]:
                resource, action = scope.rsplit("_", 1)
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
    template_name = "smart_contracts/agreement_generate_pdf.html"

    def get_page_tite(self) -> str:
        return _("Sutarties generavimas: {organization}").format(organization=self.agreement.assigner)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE, self.agreement) or self.request.user == self.object.user

    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        dispatch = super().dispatch(request, *args, **kwargs)
        if self.agreement.status == AgreementStatuses.CREATED:
            return dispatch

        error_msg = _(
            "Sutarties dokumentas gali būti generuojamas sutarčiai su "
            "būsena {accepted_status}. Dabartinė būsena: {current_status}"
        ).format(
            accepted_status=AgreementStatuses.CREATED,
            current_status=self.agreement.status,
        )
        messages.error(request, error_msg)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self) -> str:
        return reverse("agreement-detail", args=[self.object.pk, self.agreement.pk])

    @transaction.atomic
    def form_valid(self, form: AgreementGeneratePdfForm) -> HttpResponse:
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


class AgreementUploadSignedFile(
    LoginRequiredMixin,
    BaseProjectMixin,
    BaseAgreementMixin,
    PermissionRequiredMixin,
    FormView,
):
    form_class = AgreementUploadForm
    template_name = "base_form.html"

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE, self.agreement) or self.request.user == self.object.user

    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        dispatch = super().dispatch(request, *args, **kwargs)
        accepted_statuses = (AgreementStatuses.FORMED, AgreementStatuses.INITIATED)
        if self.agreement.status in accepted_statuses:
            return dispatch

        error_msg = _(
            "Sutarties dokumentas gali būti generuojamas sutarčiai su "
            "būsenomis {accepted_statuses}. Dabartinė būsena: {current_status}"
        ).format(
            accepted_statuses=", ".join(accepted_statuses),
            current_status=self.agreement.status,
        )
        messages.error(request, error_msg)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        agreement_details_title = _("Sutartis: {organization}").format(organization=self.agreement.assigner)
        page_title = (
            _("Įkelti gavėjo pasirašytą dokumentą")
            if self.agreement.status == AgreementStatuses.FORMED
            else _("Įkelti tiekėjo pasirašytą dokumentą")
        )

        context.update(
            {
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("project-list"): _("Panaudojimo atvejai"),
                    reverse("project-detail", args=[self.object.pk]): self.object,
                    reverse("agreement-list", args=[self.object.pk]): _("Sutartys"),
                    reverse("agreement-detail", args=[self.object.pk, self.agreement.pk]): agreement_details_title,
                    None: page_title,
                },
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
