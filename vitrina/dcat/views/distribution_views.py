import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.http import HttpResponseBase, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.functional import cached_property
from django.views.generic import DeleteView
from parler.views import TranslatableCreateView, TranslatableUpdateView

from vitrina.datasets.models import Dataset
from vitrina.dcat.wizard import wizard_node_type
from vitrina.orgs.models import Organization
from vitrina.dcat.forms.distribution_forms import DatasetDistributionForm
from vitrina.orgs.services import has_perm, Action
from vitrina.resources.models import DatasetDistribution

from django.utils.translation import gettext_lazy as _, get_language

from vitrina.dcat.view_helpers import (
    can_delete_distribution_in_wizard,
    datasets_in_org_scope,
    wizard_breadcrumb_ancestors,
)
from vitrina.dcat.views.dataset_views import _render_dataset_fragment
from vitrina.resources.view_helpers import get_default_distribution_name
from vitrina.structure.models import Version


class DcatDistributionCreateView(LoginRequiredMixin, PermissionRequiredMixin, TranslatableCreateView):
    model = DatasetDistribution
    template_name = "vitrina/dcat/_wizard_distribution_create_fragment.html"
    form_class = DatasetDistributionForm

    @cached_property
    def dataset(self) -> Dataset:
        organization = get_object_or_404(Organization, pk=self.kwargs.get("organization_id"))
        return get_object_or_404(
            datasets_in_org_scope(organization).select_related("organization", "subclass"),
            pk=self.kwargs.get("dataset_id"),
        )

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.CREATE_WIZARD, DatasetDistribution, self.dataset)

    def dispatch(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        if self.dataset.is_public:
            messages.warning(request, _("Vedlio negalima naudoti su atvirais duomenų ištekliais"))
            return HttpResponseRedirect(reverse("organization-detail", kwargs={"pk": self.dataset.organization.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.dataset

        return kwargs

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Nauja duomenų rinkinio pateiktis")
        context["dataset"] = self.dataset
        context["wizard_create_post_url"] = reverse(
            "dcat-distribution-create",
            kwargs={
                "organization_id": self.dataset.organization_id,
                "dataset_id": self.dataset.pk,
            },
        )
        context["breadcrumb_ancestors"] = wizard_breadcrumb_ancestors(
            self.dataset, self.dataset.organization, include_self=True
        )
        return context

    def form_valid(self, form: DatasetDistributionForm) -> HttpResponseBase:
        distribution = form.save(commit=False)
        distribution.dataset = self.dataset

        if not (name := form.cleaned_data.get("name")):
            name = get_default_distribution_name(self.dataset)
        distribution.name = name
        distribution.save()

        if "documentation" in form.changed_data:
            distribution.update_documentation(form.cleaned_data["documentation"])

        if "conforms_to" in form.changed_data:
            distribution.conforms_to.set(form.cleaned_data["conforms_to"])

        if "languages" in form.changed_data:
            distribution.languages.set(form.cleaned_data["languages"])

        messages.success(self.request, _("Pateiktis sukurta sėkmingai!"))

        distribution.set_current_language(get_language())
        update_form = DatasetDistributionForm(instance=distribution, dataset=distribution.dataset)
        update_form.helper.form_tag = False
        context = {
            "form": update_form,
            "object": distribution,
            "breadcrumb_ancestors": wizard_breadcrumb_ancestors(
                distribution.dataset, distribution.dataset.organization, include_self=True
            ),
        }
        response = render(self.request, "vitrina/dcat/_wizard_distribution_fragment.html", context)
        response["HX-Trigger"] = json.dumps(
            {
                "treeRefresh": None,
                "wizardnodecreated": {"nodeKey": f"distribution:{distribution.pk}"},
            }
        )
        return response


class DcatDistributionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, TranslatableUpdateView):
    model = DatasetDistribution
    template_name = "vitrina/dcat/_wizard_distribution_fragment.html"
    form_class = DatasetDistributionForm
    pk_url_kwarg = "distribution_id"

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE_WIZARD, self.get_object())

    def _wizard_notice(self, message: str) -> HttpResponseBase:
        from django.http import HttpResponse

        return HttpResponse(f'<div class="notification is-warning is-light">{message}</div>')

    def dispatch(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        distribution = self.get_object()
        if (version_id := kwargs.get("version_id")) is not None:
            metadata_version = get_object_or_404(Version, pk=version_id)
            if not metadata_version.is_draft():
                return self._wizard_notice(
                    str(_("Negalima redaguoti pateikties, kai versijos būsena nėra juodraštis."))
                )

        if distribution.dataset.is_public:
            return self._wizard_notice(str(_("Vedlio negalima naudoti su atvirais duomenų ištekliais.")))

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        organization = get_object_or_404(Organization, pk=self.kwargs.get("organization_id"))
        scoped_dataset_ids = datasets_in_org_scope(organization).values_list("pk", flat=True)
        return (
            super()
            .get_queryset()
            .filter(
                dataset_id__in=scoped_dataset_ids,
                dataset_id=self.kwargs.get("dataset_id"),
            )
            .select_related("dataset__organization", "dataset__subclass")
        )

    def get_form_kwargs(self) -> dict:
        kwargs = super().get_form_kwargs()
        kwargs["dataset"] = self.get_object().dataset

        return kwargs

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Duomenų rinkinio pateikties redagavimas")
        form = context.get("form")
        if form and hasattr(form, "helper"):
            form.helper.form_tag = False
        distribution = self.get_object()
        context["breadcrumb_ancestors"] = wizard_breadcrumb_ancestors(
            distribution.dataset, distribution.dataset.organization, include_self=True
        )
        context["can_delete"] = can_delete_distribution_in_wizard(distribution)
        return context

    def form_valid(self, form: DatasetDistributionForm) -> HttpResponseBase:
        distribution = form.save(commit=False)  # Skip saving m2m. We will save it manually
        distribution.save()

        if metadata := distribution.metadata.first():
            metadata.name = form.cleaned_data.get("name")
            metadata.title = form.cleaned_data.get("title")
            metadata.description = form.cleaned_data.get("description")
            metadata.version += 1
            metadata.save()

        if "documentation" in form.changed_data:
            distribution.update_documentation(form.cleaned_data["documentation"])

        if "conforms_to" in form.changed_data:
            distribution.conforms_to.set(form.cleaned_data["conforms_to"])

        if "languages" in form.changed_data:
            distribution.languages.set(form.cleaned_data["languages"])

        messages.success(self.request, _("Pateiktis atnaujinta sėkmingai!"))

        distribution.set_current_language(get_language())
        fresh_form = DatasetDistributionForm(instance=distribution, dataset=distribution.dataset)
        fresh_form.helper.form_tag = False
        response = render(
            self.request,
            "vitrina/dcat/_wizard_distribution_fragment.html",
            self.get_context_data(form=fresh_form),
        )
        response["HX-Trigger"] = "treeRefresh"
        return response


class DcatDistributionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = DatasetDistribution
    pk_url_kwarg = "distribution_id"
    template_name = "vitrina/dcat/_wizard_dataset_delete_fragment.html"

    @cached_property
    def organization(self) -> Organization:
        return get_object_or_404(Organization, pk=self.kwargs["organization_id"])

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.DELETE_WIZARD, self.get_object())

    def _wizard_notice(self, message: str) -> HttpResponseBase:
        distribution = self.get_object()
        distribution.set_current_language(get_language())
        messages.warning(self.request, message)
        form = DatasetDistributionForm(instance=distribution, dataset=distribution.dataset)
        form.helper.form_tag = False
        context = {
            "object": distribution,
            "form": form,
            "breadcrumb_ancestors": wizard_breadcrumb_ancestors(
                distribution.dataset, self.organization, include_self=True
            ),
            "can_delete": False,
        }
        return render(self.request, "vitrina/dcat/_wizard_distribution_fragment.html", context)

    def dispatch(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        obj = self.get_object()
        if not can_delete_distribution_in_wizard(obj):
            return self._wizard_notice(str(_("Šios pateikties ištrinti negalima.")))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        scoped_dataset_ids = datasets_in_org_scope(self.organization).values_list("pk", flat=True)
        return (
            super()
            .get_queryset()
            .filter(dataset_id__in=scoped_dataset_ids, dataset_id=self.kwargs.get("dataset_id"))
            .select_related("dataset__organization", "dataset__subclass")
        )

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        context["breadcrumb_ancestors"] = wizard_breadcrumb_ancestors(
            self.object.dataset, self.organization, include_self=True
        )
        context["form_title"] = _("Pateiktis")
        context["cancel_url"] = reverse(
            "dcat-distribution-update",
            kwargs={
                "organization_id": self.organization.pk,
                "dataset_id": self.object.dataset_id,
                "distribution_id": self.object.pk,
            },
        )
        context["delete_url"] = reverse(
            "dcat-distribution-delete",
            kwargs={
                "organization_id": self.organization.pk,
                "dataset_id": self.object.dataset_id,
                "distribution_id": self.object.pk,
            },
        )
        return context

    def form_valid(self, form) -> HttpResponseBase:
        dataset = self.object.dataset
        self.object.metadata.all().delete()
        self.object.delete()
        messages.success(self.request, _("Pateiktis ištrinta sėkmingai!"))

        response = _render_dataset_fragment(self.request, dataset, self.organization)
        dataset_node_key = f"{wizard_node_type(dataset)}:{dataset.pk}"
        response["HX-Trigger"] = json.dumps(
            {
                "treeRefresh": None,
                "wizardnodecreated": {"nodeKey": dataset_node_key},
            }
        )
        return response
