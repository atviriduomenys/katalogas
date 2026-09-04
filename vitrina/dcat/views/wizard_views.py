from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseBase, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, View

from vitrina.datasets.models import DCATResourceSubclass
from vitrina.dcat.wizard import (
    WIZARD_ALLOWED_PARENTS,
    WIZARD_CREATABLE_TYPES,
    WIZARD_NODE_HELPERS,
    WIZARD_NODE_ICONS,
    WIZARD_NODE_LABELS,
    WIZARD_NODE_ORGANIZATION,
    WIZARD_NODE_DISTRIBUTION,
    WIZARD_TYPE_TO_SUBCLASS_NAME,
    _build_wizard_tree,
)
from vitrina.orgs.models import Organization
from vitrina.orgs.services import can_manage_is_metadata
from vitrina.orgs.views import OrganizationBaseViewMixin


class WizardAccessMixin(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganizationBaseViewMixin,
):
    """Access rules shared by every view of the IS metadata wizard."""

    organization: Organization

    def has_permission(self) -> bool:
        return can_manage_is_metadata(self.request.user, self.organization)

    def handle_no_permission(self) -> HttpResponseBase:
        # ``LoginRequiredMixin`` routes anonymous requests here too; ``super()`` keeps ``next``.
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return redirect("organization-detail", pk=self.organization.pk)


class OrganizationWizardView(WizardAccessMixin, TemplateView):
    template_name = "vitrina/orgs/wizard.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        tree, nodes_by_key = _build_wizard_tree(self.organization)
        context["wizard_tree"] = tree
        context["wizard_node_labels"] = WIZARD_NODE_LABELS
        context["wizard_nodes_json"] = nodes_by_key
        context["wizard_node_meta_json"] = {
            node_type: {
                "type_label": str(WIZARD_NODE_LABELS[node_type]),
                "icon": WIZARD_NODE_ICONS[node_type],
                "helper": str(WIZARD_NODE_HELPERS.get(node_type, "")),
                "parents_label": ", ".join(
                    str(WIZARD_NODE_LABELS[parent_type]) for parent_type in WIZARD_ALLOWED_PARENTS.get(node_type, [])
                ),
            }
            for node_type in WIZARD_CREATABLE_TYPES
        }
        context["wizard_creatable_types_json"] = WIZARD_CREATABLE_TYPES
        context["parent_links"].update({None: _("IS metaduomenys")})
        return context


class OrganizationWizardTreeView(WizardAccessMixin, TemplateView):
    template_name = "vitrina/orgs/_wizard_tree_children_fragment.html"

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        tree, _ = _build_wizard_tree(self.organization)
        context["wizard_tree"] = tree
        return context


class OrganizationWizardNodesView(WizardAccessMixin, View):
    def get(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        _, nodes_by_key = _build_wizard_tree(self.organization)
        return JsonResponse(nodes_by_key)


class OrganizationWizardCreateRedirectView(WizardAccessMixin, View):
    def get(self, request: WSGIRequest, *args, **kwargs) -> HttpResponseBase:
        child_type = request.GET.get("type", "")
        parent_type = request.GET.get("parent_type", "")
        parent_id_str = request.GET.get("parent_id", "")
        org = self.organization

        if child_type == WIZARD_NODE_DISTRIBUTION:
            try:
                parent_id = int(parent_id_str)
            except (ValueError, TypeError):
                return redirect("organization-wizard", pk=org.pk)
            return redirect(
                reverse(
                    "dcat-distribution-create",
                    kwargs={
                        "organization_id": org.pk,
                        "dataset_id": parent_id,
                    },
                )
            )

        subclass_name = WIZARD_TYPE_TO_SUBCLASS_NAME.get(child_type)
        if not subclass_name:
            return redirect("organization-wizard", pk=org.pk)

        subclass = get_object_or_404(DCATResourceSubclass, name=subclass_name)

        if parent_type == WIZARD_NODE_ORGANIZATION:
            return redirect(
                reverse(
                    "dcat-dataset-create",
                    kwargs={
                        "organization_id": org.pk,
                        "subclass_uuid": subclass.pk,
                    },
                )
            )

        try:
            parent_id = int(parent_id_str)
        except (ValueError, TypeError):
            return redirect("organization-wizard", pk=org.pk)

        return redirect(
            reverse(
                "dcat-dataset-create-with-parent",
                kwargs={
                    "organization_id": org.pk,
                    "parent_id": parent_id,
                    "subclass_uuid": subclass.pk,
                },
            )
        )
