from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from reversion import set_comment
from reversion.models import Version, Revision
from reversion.views import RevisionMixin

from vitrina.orgs.forms import OrganizationPlanForm
from vitrina.orgs.models import Representative, Organization
from vitrina.orgs.services import has_perm, Action
from vitrina.plans.models import Plan
from vitrina.plans.services import has_plan_close_permission
from vitrina.views import PlanMixin, HistoryView


class PlanDetailView(PlanMixin, DetailView):
    model = Plan
    template_name = 'vitrina/plans/detail.html'
    plan_url_name = 'organization-plans'
    pk_url_kwarg = 'plan_id'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_plan_object(self):
        return self.organization

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_manage'] = has_perm(
            self.request.user,
            Action.PLAN,
            self.organization
        )
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.organization
        )
        context['can_manage_history'] = has_perm(
            self.request.user,
            Action.HISTORY_VIEW,
            self.organization,
        )
        context['can_close'] = has_plan_close_permission(self.request.user, self.object)
        context['organization'] = self.organization
        context['organization_id'] = self.organization.pk
        context['plan_requests'] = self.object.planrequest_set.all()
        context['plan_datasets'] = self.object.plandataset_set.all()
        context['history_url'] = reverse('plan-history', args=[self.organization.pk, self.object.pk])
        context['history_url_name'] = 'plan-hisotry'
        return context


class PlanUpdateView(PermissionRequiredMixin, RevisionMixin, UpdateView):
    model = Plan
    form_class = OrganizationPlanForm
    template_name = 'vitrina/plans/form.html'
    pk_url_kwarg = 'plan_id'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.PLAN,
            self.organization
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organizations'] = [self.organization]
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Termino redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
        }
        return context

    def form_valid(self, form):
        resp = super().form_valid(form)
        set_comment(_(f'Redaguotas terminas "{self.object}"'))
        return resp


class PlanDeleteView(PermissionRequiredMixin, RevisionMixin, DeleteView):
    model = Plan
    pk_url_kwarg = 'plan_id'
    template_name = 'confirm_delete.html'

    organization: Organization

    def dispatch(self, request, *args, **kwargs):
        self.organization = get_object_or_404(Organization, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.PLAN,
            self.organization
        )

    def get_success_url(self):
        return reverse('organization-plans', args=[self.organization.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Termino pašalinimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[self.organization.pk]): self.organization.title,
        }
        return context

    def delete(self, request, *args, **kwargs):
        from datetime import datetime
        resp = super().delete(request, *args, **kwargs)
        revision = Revision.objects.create(
            date_created=datetime.now(),
            user=self.request.user,
            comment=f'Pašalintas terminas "{self.object}"',
        )
        return resp


class PlanHistoryView(PlanMixin, HistoryView):
    model = Organization
    detail_url_name = "organization-detail"
    history_url_name = "plan-history"
    plan_url_name = 'plan-detail'
    tabs_template_name = 'vitrina/orgs/tabs.html'

    plan: Plan

    def dispatch(self, request, *args, **kwargs):
        self.plan = get_object_or_404(Plan, pk=kwargs.get('plan_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['organization_id'] = self.object.pk
        return context

    def get_history_objects(self):
        return (
            Version.objects.
            get_for_object(self.plan).
            order_by('-revision__date_created')
        )

    def get_history_url(self):
        return reverse('plan-history', args=[self.object.pk, self.plan.pk])

    def get_plan_url(self):
        return self.plan.get_absolute_url()


class PlanCloseView(PermissionRequiredMixin, View):
    plan: Plan
    is_closed = True

    def dispatch(self, request, *args, **kwargs):
        self.plan = get_object_or_404(Plan, pk=kwargs.get('plan_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_plan_close_permission(self.request.user, self.plan)

    def get(self, request, *args, **kwargs):
        self.plan.is_closed = self.is_closed
        self.plan.save()
        return redirect(self.plan.get_absolute_url())


class PlanOpenView(PlanCloseView):
    is_closed = False
