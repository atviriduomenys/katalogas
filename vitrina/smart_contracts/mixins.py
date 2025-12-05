import os
from typing import Any, Callable

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.files.base import ContentFile
from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.db.models import Prefetch
from django.forms.models import ModelForm
from django.http import HttpResponseRedirect
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from vitrina.datasets.models import Dataset
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
    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.agreement = get_object_or_404(
            Agreement.objects.all().select_related("assigner").prefetch_related("scopes"),
            project=self.project,
            pk=self.kwargs["agreement_id"],
        )


class AgreementNegotiateMixin(BaseAgreementMixin, LoginRequiredMixin, PermissionRequiredMixin, FormView):
    template_name = None
    form_class = None
    title = ""

    detail_url_name = None
    history_url_name = None

    def has_permission(self) -> None:
        raise NotImplementedError

    def validate_status(self, expected_status: str) -> bool:
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


class AgreementUploadSignedFileMixin:
    expected_status: AgreementStatuses | None = None
    next_status: AgreementStatuses | None = None
    signer_check: Callable[[User, Agreement], bool] | None = None
    success_message: str | None = None

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

        if error := self._validate_pdf_state():
            messages.error(request, error)
            return HttpResponseRedirect(self.get_success_url())

        has_expected_status = self.agreement.status == self.expected_status
        is_valid_signer = self.signer_role_check and self.signer_role_check(request.user, self.agreement)
        if has_expected_status and not is_valid_signer:
            messages.error(request, self.signer_error_message)
            return HttpResponseRedirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def _validate_pdf_state(self) -> str | None:
        count = AgreementFile.objects.filter(
            agreement=self.agreement,
            file__iendswith=AgreementFile.AllowedFileTypes.PDF,
        ).count()

        if count == 0:
            return _("PDF failas sutarčiai nėra sukurtas.")
        elif count > 1:
            return _("Rasti keli PDF failai. Susisiekite su administratoriumi.")
        return None

    @transaction.atomic
    def form_valid(self, form: ModelForm) -> HttpResponseRedirect:
        if not self.validate_status(self.expected_status):
            return HttpResponseRedirect(self.get_success_url())

        self._execute_action(form)

        return HttpResponseRedirect(self.get_success_url())

    def _execute_action(self, form: ModelForm) -> None:
        uploaded_file = form.cleaned_data["file"]

        self.agreement.status = self.next_status
        self.agreement.save()

        AgreementFile.objects.create(
            agreement=self.agreement,
            file_name=uploaded_file.name,
            file=uploaded_file,
        )

        messages.success(self.request, self.success_message)


class AgreementSubmitMixin:
    form_class = AgreementSubmitForm
    title = _("Pateikti pasiūlymą")
    expected_status = AgreementStatuses.CREATED

    def _execute_action(self, form: ModelForm) -> HttpResponse:
        if not self.validate_status(self.expected_status):
            return HttpResponseRedirect(self.get_success_url())

        self.agreement.status = AgreementStatuses.SUBMITTED
        self.agreement.assignee_representative = form.cleaned_data["assignee_representative"]
        self.agreement.save()

        messages.success(self.request, _("Pasiūlymas sėkmingai pateiktas duomenų teikėjui."))
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form: ModelForm) -> HttpResponse:
        return self._execute_action(form)


class AgreementApproveMixin:
    form_class = AgreementApproveForm
    title = _("Patvirtinti pasiūlymą")
    expected_status = AgreementStatuses.SUBMITTED

    def _execute_action(self, form: ModelForm) -> HttpResponse:
        if not self.validate_status(self.expected_status):
            return HttpResponseRedirect(self.get_success_url())

        self.agreement.status = AgreementStatuses.APPROVED
        self.agreement.template = form.cleaned_data["template"]
        self.agreement.assigner_representative = form.cleaned_data["assigner_representative"]
        self.agreement.other_assigner_legislations = form.cleaned_data["other_assigner_legislations"]
        self.agreement.save()

        messages.success(self.request, _("Pasiūlymas sėkmingai patvirtintas."))
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form: ModelForm) -> HttpResponse:
        return self._execute_action(form)


class AgreementFormMixin:
    form_class = AgreementFormForm
    title = _("Formuoti sutartį")
    expected_status = AgreementStatuses.APPROVED

    def _execute_action(self, form: ModelForm) -> HttpResponse:
        if not self.validate_status(AgreementStatuses.APPROVED):
            return HttpResponseRedirect(self.get_success_url())

        template = self.agreement.template

        self.agreement.status = AgreementStatuses.FORMED
        self.agreement.save()

        self.agreement.generate_contract_pdf_file(template=template)
        file_name, extension = os.path.splitext(os.path.basename(template.file.name))
        copy_file_name = f"{file_name}_copy{extension}"
        with template.file.open() as file:
            self.agreement.files.create(
                file=ContentFile(content=file.read(), name=copy_file_name),
                is_template=True,
                file_name=copy_file_name,
            )

        messages.success(self.request, _("Sutarties dokumentas sukurtas"))
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form: ModelForm) -> HttpResponse:
        return self._execute_action(form)


class AgreementInitiateMixin(AgreementUploadSignedFileMixin):
    form_class = AgreementInitiateForm
    title = _("Įkelti pasirašytą sutartį")

    expected_status = AgreementStatuses.FORMED
    next_status = AgreementStatuses.INITIATED

    success_message = _("Sutarties dokumentas įkeltas sėkmingai.")
    signer_error_message = _("Šią sutartį šiuo metu turi pasirašyti duomenų gavėjo atstovas.")

    def signer_role_check(self, user: User, agreement: Agreement) -> bool:
        return user.viisp_organization == agreement.assignee


class AgreementSignMixin(AgreementUploadSignedFileMixin):
    form_class = AgreementSignForm
    title = _("Įkelti pasirašytą sutartį")

    expected_status = AgreementStatuses.INITIATED
    next_status = AgreementStatuses.SIGNED

    success_message = _("Sutarties dokumentas įkeltas sėkmingai.")
    signer_error_message = _("Šią sutartį šiuo metu turi pasirašyti duomenų teikėjo atstovas.")

    def signer_role_check(self, user: User, agreement: Agreement) -> bool:
        return user.viisp_organization == agreement.assigner

    def _execute_action(self, form: ModelForm) -> None:
        super()._execute_action(form)

        self.agreement.is_agent_sync_enabled = True
        self.agreement.save()


class ProjectBasedAgreementNegotiateMixin(BaseProjectMixin, AgreementNegotiateMixin):
    template_name = "smart_contracts/agreement_negotiate.html"

    detail_url_name = "project-detail"
    history_url_name = "project-history"

    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        self.object = self.get_project(kwargs["pk"])
        return super().setup(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["agreement"] = self.agreement
        return kwargs

    def get_success_url(self) -> str:
        return reverse("project-agreement-detail", args=[self.object.pk, self.agreement.pk])

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "current_title": self.title,
                "parent_links": self.get_parent_links(self.title),
                "agreement": self.agreement,
                "project": self.agreement.project,
                "datasets": self.object.datasets.filter(organization=self.agreement.assigner).all(),
            }
        )

        return context

    def get_parent_links(self, current_action_name: str) -> dict[str | None, str]:
        return {
            reverse("home"): _("Pradžia"),
            reverse("project-list"): _("Panaudojimo atvejai"),
            reverse("project-detail", args=[self.project.pk]): self.project,
            reverse("project-agreement-list", args=[self.object.pk]): _("Sutartys"),
            reverse(
                "project-agreement-detail", args=[self.object.pk, self.agreement.pk]
            ): self.agreement.detail_page_title,
            None: current_action_name,
        }
