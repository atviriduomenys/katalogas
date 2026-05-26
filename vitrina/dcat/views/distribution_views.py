import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.http import HttpResponseBase, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.functional import cached_property
from parler.views import TranslatableCreateView, TranslatableUpdateView

from vitrina.datasets.models import Dataset
from vitrina.dcat.forms.distribution_forms import DatasetDistributionForm
from vitrina.orgs.services import has_perm, Action
from vitrina.resources.models import DatasetDistribution

from django.utils.translation import gettext_lazy as _, get_language

from vitrina.dcat.view_helpers import wizard_breadcrumb_ancestors
from vitrina.resources.view_helpers import get_default_distribution_name
from vitrina.structure.models import Version


class DcatDistributionCreateView(LoginRequiredMixin, PermissionRequiredMixin, TranslatableCreateView):
    model = DatasetDistribution
    template_name = "base_form.html"
    form_class = DatasetDistributionForm

    @cached_property
    def dataset(self) -> Dataset:
        return get_object_or_404(
            Dataset.objects.select_related("organization", "subclass"),
            organization_id=self.kwargs.get("organization_id"),
            pk=self.kwargs.get("dataset_id"),
        )

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.CREATE_WIZARD, DatasetDistribution, self.dataset)

    def _is_wizard_request(self) -> bool:
        return bool(self.request.headers.get("X-Wizard-Request"))

    def get_template_names(self) -> list[str]:
        if self._is_wizard_request():
            return ["vitrina/dcat/_wizard_distribution_create_fragment.html"]
        return super().get_template_names()

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
        if self._is_wizard_request():
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

        if self._is_wizard_request():
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

        return HttpResponseRedirect(
            reverse(
                "dcat-distribution-update",
                kwargs={
                    "organization_id": self.dataset.organization_id,
                    "dataset_id": self.dataset.pk,
                    "distribution_id": distribution.pk,
                },
            )
        )


class DcatDistributionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, TranslatableUpdateView):
    model = DatasetDistribution
    template_name = "base_form.html"
    form_class = DatasetDistributionForm
    pk_url_kwarg = "distribution_id"

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE_WIZARD, self.get_object())

    def _is_wizard_request(self) -> bool:
        return bool(self.request.headers.get("X-Wizard-Request"))

    def get_template_names(self) -> list[str]:
        if self._is_wizard_request():
            return ["vitrina/dcat/_wizard_distribution_fragment.html"]
        return super().get_template_names()

    def _wizard_notice(self, message: str) -> HttpResponseBase:
        from django.http import HttpResponse

        return HttpResponse(f'<div class="notification is-warning is-light">{message}</div>')

    def dispatch(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        distribution = self.get_object()
        if (version_id := kwargs.get("version_id")) is not None:
            metadata_version = get_object_or_404(Version, pk=version_id)
            if not metadata_version.is_draft():
                if self._is_wizard_request():
                    return self._wizard_notice(
                        str(_("Negalima redaguoti pateikties, kai versijos būsena nėra juodraštis."))
                    )
                messages.error(request, _("Negalima redaguoti pateikties, kai versijos būsena nėra juodraštis."))
                return HttpResponseRedirect(
                    reverse("organization-detail", kwargs={"pk": distribution.dataset.organization.pk})
                )

        if distribution.dataset.is_public:
            if self._is_wizard_request():
                return self._wizard_notice(str(_("Vedlio negalima naudoti su atvirais duomenų ištekliais.")))
            messages.warning(request, _("Vedlio negalima naudoti su atvirais duomenų ištekliais"))
            return HttpResponseRedirect(
                reverse("organization-detail", kwargs={"pk": distribution.dataset.organization.pk})
            )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet:
        return (
            super()
            .get_queryset()
            .filter(
                dataset__organization_id=self.kwargs.get("organization_id"),
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
        if self._is_wizard_request():
            form = context.get("form")
            if form and hasattr(form, "helper"):
                form.helper.form_tag = False
            distribution = self.get_object()
            context["breadcrumb_ancestors"] = wizard_breadcrumb_ancestors(
                distribution.dataset, distribution.dataset.organization, include_self=True
            )
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

        if self._is_wizard_request():
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

        return HttpResponseRedirect(
            reverse(
                "dcat-distribution-update",
                kwargs={
                    "organization_id": distribution.dataset.organization_id,
                    "dataset_id": distribution.dataset.pk,
                    "distribution_id": distribution.pk,
                },
            )
        )
