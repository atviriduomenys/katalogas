from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, UpdateView

from vitrina.datasets.models import Contact
from vitrina.dcat.forms.contact_forms import DcatContactForm, DcatContactUpdateForm
from vitrina.orgs.models import Organization
from vitrina.orgs.services import Action, has_perm
from vitrina.orgs.views import OrganizationBaseViewMixin
from vitrina.views import PlanMixin


class DcatContactCreateView(
    LoginRequiredMixin, PermissionRequiredMixin, OrganizationBaseViewMixin, PlanMixin, CreateView
):
    model = Contact
    form_class = DcatContactForm
    template_name = "base_form.html"
    organization_url_kwarg = "organization_id"

    @cached_property
    def organization(self) -> Organization:
        return get_object_or_404(Organization, pk=self.kwargs["organization_id"])

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.CREATE_WIZARD, Contact, self.organization)

    def get_success_url(self) -> str:
        return reverse("organization-contacts", kwargs={"pk": self.organization.pk})

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Kontaktinės informacijos pridėjimas")
        context["parent_links"] = {
            self.get_success_url(): _("Kontaktai"),
            None: _("Pridėti"),
        }
        return context

    def form_valid(self, form: DcatContactForm) -> HttpResponseRedirect:
        contact = form.save(commit=False)
        contact.organization = self.organization
        contact.content_type = None
        contact.object_id = None
        contact.kind = Contact.Kind.SERVICE
        contact.save()
        form.save_m2m()
        messages.success(self.request, _("Kontaktinė informacija sėkmingai išsaugota!"))
        return HttpResponseRedirect(self.get_success_url())


class DcatContactUpdateView(
    LoginRequiredMixin, PermissionRequiredMixin, OrganizationBaseViewMixin, PlanMixin, UpdateView
):
    model = Contact
    form_class = DcatContactUpdateForm
    template_name = "base_form.html"
    pk_url_kwarg = "contact_id"
    organization_url_kwarg = "organization_id"

    @cached_property
    def organization(self) -> Organization:
        return get_object_or_404(Organization, pk=self.kwargs["organization_id"])

    def get_queryset(self):
        return super().get_queryset().filter(organization=self.organization, kind=Contact.Kind.SERVICE)

    def has_permission(self) -> bool:
        return has_perm(self.request.user, Action.UPDATE_WIZARD, self.get_object())

    def get_success_url(self) -> str:
        return reverse("organization-contacts", kwargs={"pk": self.organization.pk})

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context["current_title"] = _("Kontaktinės informacijos redagavimas")
        context["parent_links"] = {
            self.get_success_url(): _("Kontaktai"),
            None: _("Redaguoti"),
        }
        return context

    def form_valid(self, form: DcatContactUpdateForm) -> HttpResponseRedirect:
        contact = form.save(commit=False)
        contact.kind = Contact.Kind.SERVICE
        contact.save()
        form.save_m2m()
        messages.success(self.request, _("Kontaktinė informacija sėkmingai atnaujinta!"))
        return HttpResponseRedirect(self.get_success_url())
