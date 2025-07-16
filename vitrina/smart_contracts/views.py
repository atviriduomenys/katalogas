from itertools import groupby
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Prefetch
from django.forms import modelformset_factory, BaseFormSet
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseBase, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.models import Project
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.forms import (
    SmartContractForm,
    SmartContractFormSetHelper,
)
from vitrina.smart_contracts.models import Agreement, AgreementScope
from vitrina.views import FormsetView


class AgreementCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
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
        if Agreement.objects.filter(project=self.object).exists():
            messages.error(
                self.request,
                _("Šis panaudojimo atvejis jau turi egzistuojančią sutartį."),
            )
            return HttpResponseRedirect(
                reverse("project-datasets", kwargs={"pk": self.kwargs.get("pk")})
            )

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
        return reverse("project-detail", args=[self.object.pk])

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
