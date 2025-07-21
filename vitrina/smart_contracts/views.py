from itertools import groupby
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.handlers.wsgi import WSGIRequest
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.forms import modelformset_factory, BaseFormSet
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseBase, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses, AGREEMENT_STATUS_DESCRIPTIONS
from vitrina.smart_contracts.forms import (
    SmartContractForm,
    SmartContractFormSetHelper,
)
from vitrina.smart_contracts.models import Agreement, AgreementScope
from vitrina.views import FormsetView, HistoryMixin


class BaseAgreementMixin:
    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
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


class AgreementListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    BaseAgreementMixin,
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
                "can_update_project": has_perm(
                    self.request.user, Action.UPDATE, self.object
                ),
                "can_view_agreements": has_perm(
                    self.request.user, Action.VIEW, Agreement, self.object
                ),
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
    PermissionRequiredMixin,
    BaseAgreementMixin,
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

    def setup(self, request: WSGIRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        self.agreement = get_object_or_404(
            Agreement.objects.all()
            .select_related("assigner_organization")
            .prefetch_related("agreementscope_set"),
            project=self.object,
            pk=kwargs["agreement_id"],
        )

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        page_title = _("Sutartis: {organization}").format(
            organization=self.agreement.assigner_organization
        )

        context.update(
            {
                "project": self.object,
                "agreement": self.agreement,
                "agreement_files": self.agreement.agreementfile_set.all().order_by(
                    "-created_at"
                ),
                "agreement_status_descriptions": AGREEMENT_STATUS_DESCRIPTIONS,
                "page_title": page_title,
                "can_update_project": has_perm(
                    self.request.user, Action.UPDATE, self.object
                ),
                "can_view_agreements": has_perm(
                    self.request.user, Action.VIEW, Agreement, self.object
                ),
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
    PermissionRequiredMixin,
    BaseAgreementMixin,
    FormsetView,
):
    object: Project

    model = Project
    template_name = "smart_contracts/agreement_create.html"

    def has_permission(self) -> bool:
        return (
            has_perm(self.request.user, Action.UPDATE, self.object)
            or self.request.user == self.object.user
        )

    def dispatch(
        self, request: WSGIRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        if Agreement.objects.filter(project=self.object).exists():
            messages.error(
                self.request,
                _("Šis panaudojimo atvejis jau turi egzistuojančią sutartį."),
            )
            return HttpResponseRedirect(self.get_success_url())

        return super().dispatch(request, *args, **kwargs)

    def get_formset(self) -> BaseFormSet:
        formset_kwargs = self.get_formset_kwargs()
        datasets_by_organization = {
            organization: list(organization_datasets)
            for organization, organization_datasets in groupby(
                self.object.public_datasets, lambda d: d.organization
            )
        }

        SmartContractFormset = modelformset_factory(
            Organization, form=SmartContractForm, extra=0
        )
        organization_queryset = Organization.objects.filter(
            pk__in=(o.pk for o in datasets_by_organization.keys())
        ).order_by("pk")
        formset = SmartContractFormset(
            **formset_kwargs,
            queryset=organization_queryset,
            form_kwargs={"datasets_by_organization": datasets_by_organization},
        )

        return formset

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "project": self.object,
                "formset_helper": SmartContractFormSetHelper(),
                "current_title": _("Generuoti sutartį"),
                "parent_links": {
                    reverse("home"): _("Pradžia"),
                    reverse("project-list"): _("Panaudojimo atvejai"),
                    reverse("project-detail", args=[self.object.pk]): self.object,
                    None: _("Generuoti sutartį"),
                },
            }
        )

        return context

    def get_success_url(self) -> str:
        return reverse("agreement-list", args=[self.object.pk])

    def formset_valid(self, formset: BaseFormSet) -> HttpResponse:
        for form in formset:
            agreement = Agreement.objects.create(
                project=self.object,
                assigner_organization=form.instance,
                status=AgreementStatuses.CREATED,
            )
            AgreementScope.objects.bulk_create(
                [
                    AgreementScope(
                        agreement=agreement, resource=scope, action=scope.split("_")[-1]
                    )
                    for scope in form.cleaned_data["scopes"]
                ]
            )

        messages.success(self.request, _("Sutartis sėkmingai sugeneruota"))
        return super().formset_valid(formset)

    def formset_invalid(self, formset: BaseFormSet) -> HttpResponse:
        messages.error(self.request, _("Sutarties generavime kilo klaidų"))
        return super().formset_invalid(formset)
