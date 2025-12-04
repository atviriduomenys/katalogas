from itertools import groupby
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, QuerySet
from django.forms import modelformset_factory, BaseFormSet
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseBase, HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses, AGREEMENT_STATUS_DESCRIPTIONS
from vitrina.smart_contracts.forms import SmartContractForm, SmartContractFormSetHelper
from vitrina.smart_contracts.mixins import (
    BaseProjectMixin,
    BaseAgreementMixin,
    AgreementSubmitMixin,
    ProjectBasedAgreementNegotiateMixin,
    AgreementApproveMixin,
    AgreementFormMixin,
    AgreementInitiateMixin,
    AgreementSignMixin,
)
from vitrina.smart_contracts.models import Agreement, AgreementScope, AgreementFile
from vitrina.users.models import User
from vitrina.structure.models import Metadata
from vitrina.views import FormsetView
from vitrina.smart_contracts.services import get_agreements
from vitrina.smart_contracts.permissions import (
    can_view_agreements,
    can_create_agreements,
    can_view_agreement,
    can_upload_agreement_file,
    can_submit_agreements,
    can_approve_agreements,
    can_form_agreements,
    can_initiate_agreements,
    can_sign_agreements,
)


class BaseAgreementListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    model = Agreement
    template_name = None

    paginate_by = 10

    parent: object
    parent_type: str

    def get_queryset(self):
        """Override in subclasses, agreement queryset will be filtered by parent."""
        raise NotImplementedError

    def has_permission(self) -> bool:
        """Override in subclasses, permission depends on parent."""
        return False

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)

        agreements = self.get_queryset()
        paginator = Paginator(agreements, self.paginate_by)
        page = paginator.get_page(self.request.GET.get("page"))

        context.update(
            {
                "agreements": page.object_list,
                "agreement_status_descriptions": AGREEMENT_STATUS_DESCRIPTIONS,
                "page_obj": page,
                "paginator": paginator,
                "can_create_agreements": False,  # Override in subclasses.
                "parent": self.parent,
                "parent_type": self.parent_type,
            }
        )

        return context


class BaseAgreementDetailView(BaseAgreementMixin, LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = None
    parent: object = None
    parent_type: str = None

    agreement: Agreement

    def has_permission(self) -> bool:
        """Override in subclasses."""
        return False

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "agreement": self.agreement,
                "project": self.agreement.project,
                "agreement_files": self.agreement.files.all().order_by("-created_at"),
                "agreement_status_descriptions": AGREEMENT_STATUS_DESCRIPTIONS,
                "page_title": self.agreement.detail_page_title,
                "parent": self.parent,
                "parent_type": self.parent_type,
            }
        )

        return context


class ProjectBasedAgreementListView(BaseProjectMixin, BaseAgreementListView):
    template_name = "smart_contracts/agreement_list.html"
    parent_type = "project"

    def setup(self, request, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.parent: Project = self.get_project(kwargs["pk"])
        return None

    def dispatch(self, request, *args, **kwargs):
        dispatch = super().dispatch(request, *args, **kwargs)

        if not self.parent.organization:
            messages.error(
                self.request,
                _("Panaudojimo atvejis registruotas fizinio asmens vardu negali turėti sutarčių."),
            )
            return HttpResponseRedirect(reverse("project-detail", kwargs={"pk": self.project.pk}))
        return dispatch

    def has_permission(self) -> bool:
        return can_view_agreements(self.request.user, self.project)

    def get_queryset(self):
        return get_agreements(self.request.user).filter(project=self.project)

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        context["can_create_agreements"] = can_create_agreements(self.request.user, self.project)
        context["parent_links"].update({None: _("Sutartys")})
        return context


class ProjectBasedAgreementDetailView(BaseProjectMixin, BaseAgreementDetailView):
    template_name = "smart_contracts/agreement_detail.html"
    parent_type = "project"

    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.parent: Project = self.get_project(kwargs["pk"])

    def get_agreement_queryset(self) -> QuerySet:
        return Agreement.objects.filter(project=self.project)

    def has_permission(self) -> bool:
        return can_view_agreement(self.request.user, self.agreement)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "can_create_agreements": can_create_agreements(self.request.user, self.project),
                "can_submit_agreements": can_submit_agreements(self.request.user, self.agreement),
                "can_approve_agreements": can_approve_agreements(self.request.user, self.agreement),
                "can_form_agreements": can_form_agreements(self.request.user, self.agreement),
                "can_initiate_agreements": can_initiate_agreements(self.request.user, self.agreement),
                "can_sign_agreements": can_sign_agreements(self.request.user, self.agreement),
                "can_upload_agreement_file": can_upload_agreement_file(self.request.user, self.agreement),
            }
        )

        context["parent_links"].update({reverse("project-agreement-list", args=[self.project.pk]): _("Sutartys")})

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
        return reverse("project-agreement-list", args=[self.project.pk])

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


class ProjectBasedAgreementSubmitView(AgreementSubmitMixin, ProjectBasedAgreementNegotiateMixin):
    """Project-based agreement form view responsible for moving the agreement to status `SUBMITTED`"""


class ProjectBasedAgreementApproveView(AgreementApproveMixin, ProjectBasedAgreementNegotiateMixin):
    """Project-based agreement form view responsible for moving the agreement to status `APPROVED`"""


class ProjectBasedAgreementFormView(AgreementFormMixin, ProjectBasedAgreementNegotiateMixin):
    """Project-based agreement form view responsible for moving the agreement to status `FORMED`"""


class ProjectBasedAgreementInitiateView(AgreementInitiateMixin, ProjectBasedAgreementNegotiateMixin):
    """Project-based agreement form view responsible for moving the agreement to status `INITIATED`"""


class ProjectBasedAgreementSignView(AgreementSignMixin, ProjectBasedAgreementNegotiateMixin):
    """Project-based agreement form view responsible for moving the agreement to status `SIGNED`"""


class AgreementFileDownloadView(
    LoginRequiredMixin,
    BaseAgreementMixin,
    PermissionRequiredMixin,
    View,
):
    def has_permission(self) -> bool:
        return can_view_agreement(self.request.user, self.agreement)

    def get(self, request: WSGIRequest, *args, **kwargs) -> HttpResponse | FileResponse:
        agreement_file = get_object_or_404(AgreementFile, pk=self.kwargs["agreement_file_id"])

        if settings.DEBUG:
            return FileResponse(open(agreement_file.file.path, "rb"), as_attachment=True)

        response = HttpResponse()
        response["X-Accel-Redirect"] = f"/{agreement_file.file.url}"
        response["Content-Disposition"] = f'attachment; filename="{agreement_file.file_name}"'

        return response
