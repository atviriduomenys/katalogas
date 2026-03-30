from pathlib import Path
from typing import Any, Callable

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.db.models import Prefetch, QuerySet
from django.forms.models import ModelForm
from django.http import HttpResponseRedirect
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from vitrina.datasets.models import Dataset
from vitrina.helpers import get_file_extension, email
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.forms import (
    AgreementSubmitForm,
    AgreementApproveForm,
    AgreementFormForm,
    AgreementInitiateForm,
    AgreementSignForm,
)
from vitrina.smart_contracts.models import (
    Agreement,
    AgreementFile,
)
from vitrina.smart_contracts.permissions import (
    can_submit_agreements,
    can_approve_agreements,
    can_form_agreements,
    can_initiate_agreements,
    can_sign_agreements,
)
from vitrina.users.models import User
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
    def get_agreement_queryset(self) -> QuerySet:
        return Agreement.objects.all()

    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.agreement = get_object_or_404(
            self.get_agreement_queryset().select_related("assigner").prefetch_related("scopes"),
            pk=self.kwargs["agreement_id"],
        )


class AgreementNegotiateMixin(BaseAgreementMixin, LoginRequiredMixin, FormView):
    template_name = None
    form_class = None
    title = ""

    detail_url_name = None
    history_url_name = None

    def has_permission(self) -> None:
        raise NotImplementedError

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["agreement"] = self.agreement
        return kwargs


class AgreementActionMixin:
    """Mixin with common logic for all agreement status change views."""

    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.has_permission():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form: ModelForm) -> HttpResponse:
        if self.expected_status and not self.validate_status(self.expected_status):
            return HttpResponseRedirect(self.get_success_url())

        self.perform_action(form)
        if self.next_status:
            self.agreement.status = self.next_status
        self.agreement.save()

        messages.success(self.request, self.success_message or _("Veiksmas įvykdytas sėkmingai."))
        return HttpResponseRedirect(self.get_success_url())

    def perform_action(self, form: ModelForm) -> None:
        """Override in child classes for extra per-action logic."""
        return None

    def validate_status(self, expected_status: AgreementStatuses) -> bool:
        if self.agreement.status != expected_status:
            error_message = _(
                "Veiksmas gali būti atliekamas tik sutarčiai esant būsenoje {expected_status}."
                "Dabartinė būsena: {current_status}."
            ).format(
                expected_status=expected_status,
                current_status=self.agreement.status,
            )
            messages.error(self.request, error_message)
            return False
        return True


class AgreementUploadSignedFileMixin(AgreementActionMixin):
    """Mixin holding the common logic for Initiate/Sign status change for agreements."""

    expected_status: AgreementStatuses | None = None
    next_status: AgreementStatuses | None = None
    signer_role_check: Callable[[User, Agreement], bool] | None = None
    success_message: str | None = None
    signer_error_message: str | None = None

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["agreement_pdf"] = get_object_or_404(
            AgreementFile,
            agreement=self.agreement,
            file__iendswith=AgreementFile.AllowedFileTypes.PDF,
        )
        return kwargs

    def dispatch(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.has_permission():
            return self.handle_no_permission()

        count = AgreementFile.objects.filter(
            agreement=self.agreement,
            file__iendswith=AgreementFile.AllowedFileTypes.PDF,
        ).count()
        if count == 0:
            messages.error(request, _("PDF failas sutarčiai nėra sukurtas."))
            return HttpResponseRedirect(self.get_success_url())
        elif count > 1:
            messages.error(request, _("Rasti keli PDF failai. Susisiekite su administratoriumi."))
            return HttpResponseRedirect(self.get_success_url())

        has_expected_status = self.agreement.status == self.expected_status
        is_valid_signer = self.signer_role_check and self.signer_role_check(request.user, self.agreement)
        if has_expected_status and not is_valid_signer:
            messages.error(request, self.signer_error_message)
            return HttpResponseRedirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def perform_action(self, form: ModelForm) -> None:
        uploaded_file = form.cleaned_data["file"]
        AgreementFile.objects.create(
            agreement=self.agreement,
            file_name=uploaded_file.name,
            file=uploaded_file,
            file_extension=AgreementFile.AllowedFileTypes(get_file_extension(uploaded_file.name)),
        )


class AgreementSubmitMixin(AgreementActionMixin):
    form_class = AgreementSubmitForm
    title = _("Pateikti pasiūlymą")

    expected_status = AgreementStatuses.CREATED
    next_status = AgreementStatuses.SUBMITTED

    success_message = _("Pasiūlymas sėkmingai pateiktas duomenų teikėjui.")

    def has_permission(self) -> bool:
        return can_submit_agreements(self.request.user, self.agreement)

    def perform_action(self, form: ModelForm) -> None:
        self.agreement.assignee_representative = form.cleaned_data["assignee_representative"]
        if self.agreement.assigner.email:
            link = self.request.build_absolute_uri(self.get_success_url())
            email(
                [self.agreement.assigner.email],
                "agreement-submitted",
                "vitrina/smart_contracts/emails/agreement_submitted.md",
                {
                    "project": self.agreement.project.title,
                    "assignee": self.agreement.assignee.title,
                    "link": link,
                },
            )


class AgreementApproveMixin(AgreementActionMixin):
    form_class = AgreementApproveForm
    title = _("Patvirtinti pasiūlymą")

    expected_status = AgreementStatuses.SUBMITTED
    next_status = AgreementStatuses.APPROVED

    success_message = _("Pasiūlymas sėkmingai patvirtintas.")

    def has_permission(self) -> bool:
        return can_approve_agreements(self.request.user, self.agreement)

    def perform_action(self, form: ModelForm) -> None:
        self.agreement.template = form.cleaned_data["template"]
        self.agreement.assigner_representative = form.cleaned_data["assigner_representative"]
        self.agreement.other_assigner_legislations = form.cleaned_data["other_assigner_legislations"]


class AgreementFormMixin(AgreementActionMixin):
    form_class = AgreementFormForm
    title = _("Formuoti sutartį")

    expected_status = AgreementStatuses.APPROVED
    next_status = AgreementStatuses.FORMED

    success_message = _("Sutarties dokumentas sukurtas sėkmingai.")

    def has_permission(self) -> bool:
        return can_form_agreements(self.request.user, self.agreement)

    def perform_action(self, form: ModelForm) -> None:
        template = self.agreement.template
        self.agreement.generate_contract_pdf_file(template=template)
        template_file_path = Path(template.file.name)
        copy_file_name = f"{template_file_path.stem}_copy{template_file_path.suffix}"
        with template.file.open() as file:
            self.agreement.files.create(
                file=ContentFile(content=file.read(), name=copy_file_name),
                is_template=True,
                file_name=copy_file_name,
                file_extension=AgreementFile.AllowedFileTypes(get_file_extension(copy_file_name)),
            )


class AgreementInitiateMixin(AgreementUploadSignedFileMixin):
    form_class = AgreementInitiateForm
    title = _("Įkelti pasirašytą sutartį")

    expected_status = AgreementStatuses.FORMED
    next_status = AgreementStatuses.INITIATED

    success_message = _("Sutarties dokumentas įkeltas sėkmingai.")
    signer_error_message = _("Šią sutartį šiuo metu turi pasirašyti duomenų gavėjo atstovas.")

    def has_permission(self) -> bool:
        return can_initiate_agreements(self.request.user, self.agreement)

    @staticmethod
    def signer_role_check(user: User, agreement: Agreement) -> bool:
        return user.viisp_organization == agreement.assignee


class AgreementSignMixin(AgreementUploadSignedFileMixin):
    form_class = AgreementSignForm
    title = _("Įkelti pasirašytą sutartį")

    expected_status = AgreementStatuses.INITIATED
    next_status = AgreementStatuses.SIGNED

    success_message = _("Sutarties dokumentas įkeltas sėkmingai.")
    signer_error_message = _("Šią sutartį šiuo metu turi pasirašyti duomenų teikėjo atstovas.")

    def has_permission(self) -> bool:
        return can_sign_agreements(self.request.user, self.agreement)

    @staticmethod
    def signer_role_check(user: User, agreement: Agreement) -> bool:
        return user.viisp_organization == agreement.assigner

    def perform_action(self, form: ModelForm) -> None:
        super().perform_action(form)
        self.agreement.is_agent_sync_enabled = True


class ProjectBasedAgreementNegotiateMixin(BaseProjectMixin, AgreementNegotiateMixin):
    """Mixin class used for project-based agreement status-change views"""

    template_name = "smart_contracts/agreement_negotiate.html"

    detail_url_name = "project-detail"
    history_url_name = "project-history"

    def get_agreement_queryset(self) -> QuerySet:
        return Agreement.objects.filter(project=self.project)

    def get_success_url(self) -> str:
        return reverse("project-agreement-detail", args=[self.project.pk, self.agreement.pk])

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "current_title": self.title,
                "parent_links": self.get_parent_links(self.title),
                "agreement": self.agreement,
                "project": self.project,
                "datasets": self.project.datasets.all(),
            }
        )

        return context

    def get_parent_links(self, current_action_name: str) -> dict[str | None, str]:
        project_pk = self.project.pk
        return {
            reverse("home"): _("Pradžia"),
            reverse("project-list"): _("Panaudojimo atvejai"),
            reverse("project-detail", args=[project_pk]): self.project,
            reverse("project-agreement-list", args=[project_pk]): _("Sutartys"),
            reverse("project-agreement-detail", args=[project_pk, self.agreement.pk]): self.agreement.detail_page_title,
            None: current_action_name,
        }
