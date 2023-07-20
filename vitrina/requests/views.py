from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, DeleteView
from reversion.models import Version

from vitrina.datasets.forms import PlanForm
from vitrina.orgs.services import has_perm, Action
from reversion import set_comment

from vitrina.plans.models import Plan, PlanRequest
from vitrina.requests.forms import RequestForm, RequestPlanForm
from django.core.exceptions import ObjectDoesNotExist
from reversion.views import RevisionMixin
from vitrina.datasets.models import Dataset
from vitrina.requests.models import Request, RequestStructure

from django.utils.translation import gettext_lazy as _

from vitrina.views import HistoryView, HistoryMixin, PlanMixin


class RequestListView(ListView):
    model = Request
    queryset = Request.public.order_by('-created')
    template_name = 'vitrina/requests/list.html'
    paginate_by = 20


class RequestDetailView(HistoryMixin, PlanMixin, DetailView):
    model = Request
    template_name = 'vitrina/requests/detail.html'
    context_object_name = 'request_object'
    detail_url_name = 'request-detail'
    history_url_name = 'request-history'
    plan_url_name = 'request-plans'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        request: Request = self.object

        extra_context_data = {
            "formats": request.format.replace(" ", "").split(",") if request.format else [],
            "changes": request.changes.replace(" ", "").split(",") if request.changes else [],
            "purposes": request.purpose.replace(" ", "").split(",") if request.purpose else [],
            "structure": RequestStructure.objects.filter(request_id=request.pk),
            "related_object": request.object,
            "status": request.get_status_display(),
            "user_count": 0,
            'can_update_request': has_perm(
                self.request.user,
                Action.UPDATE,
                request
            )
        }
        context_data.update(extra_context_data)
        return context_data


class RequestCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    CreateView
):
    model = Request
    form_class = RequestForm
    template_name = 'base_form.html'

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, Request)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.status = Request.CREATED
        self.object.save()
        set_comment(Request.CREATED)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Poreikio registravimas')
        return context_data


class RequestUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Request
    form_class = RequestForm
    template_name = 'base_form.html'
    context_object_name = 'request_object'

    def form_valid(self, form):
        super().form_valid(form)
        set_comment(Request.EDITED)
        return HttpResponseRedirect(self.get_success_url())

    def has_permission(self):
        request = get_object_or_404(Request, pk=self.kwargs.get('pk'))
        return has_perm(self.request.user, Action.UPDATE, request)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Poreikio redagavimas')
        return context_data


class RequestHistoryView(PlanMixin, HistoryView):
    model = Request
    detail_url_name = "request-detail"
    history_url_name = "request-history"
    tabs_template_name = 'vitrina/requests/tabs.html'
    plan_url_name = 'request-plans'


class RequestPlanView(HistoryMixin, PlanMixin, TemplateView):
    template_name = 'vitrina/requests/plans.html'
    detail_url_name = 'request-detail'
    history_url_name = 'request-plans-history'
    plan_url_name = 'request-plans'

    request_obj: Request

    def dispatch(self, request, *args, **kwargs):
        self.request_obj = get_object_or_404(Request, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_obj'] = self.request_obj
        context['plans'] = self.request_obj.planrequest_set.all()
        context['can_manage_plans'] = has_perm(
            self.request.user,
            Action.PLAN,
            self.request_obj
        )
        return context

    def get_plan_object(self):
        return self.request_obj

    def get_detail_object(self):
        return self.request_obj

    def get_history_object(self):
        return self.request_obj


class RequestCreatePlanView(PermissionRequiredMixin, RevisionMixin, CreateView):
    model = Plan
    form_class = PlanForm
    template_name = 'vitrina/plans/form.html'

    request_obj: Request

    def dispatch(self, request, *args, **kwargs):
        self.request_obj = get_object_or_404(Request, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.PLAN, self.request_obj)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Naujas planas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('request-list'): _('Poreikiai ir pasiūlymai'),
            reverse('request-detail', args=[self.request_obj.pk]): self.request_obj.title,
        }
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['obj'] = self.request_obj
        kwargs['user'] = self.request.user
        kwargs['organization'] = self.request_obj.organization
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        PlanRequest.objects.create(
            plan=self.object,
            request=self.request_obj
        )
        self.request_obj.status = Request.APPROVED
        self.request_obj.save()

        set_comment(_(f'Pridėtas planas "{self.object}". Į planą įtrauktas poreikis "{self.request_obj}".'))
        return redirect(reverse('request-plans', args=[self.request_obj.pk]))


class RequestIncludePlanView(PermissionRequiredMixin, RevisionMixin, CreateView):
    form_class = RequestPlanForm
    template_name = 'base_form.html'

    request_obj: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.request_obj = get_object_or_404(Request, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.PLAN, self.request_obj)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request_obj
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Poreikio įtraukimas į planą")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('request-list'): _('Poreikiai ir pasiūlymai'),
            reverse('request-detail', args=[self.request_obj.pk]): self.request_obj.title,
        }
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.request = self.request_obj
        self.object.save()
        self.request_obj.status = Request.APPROVED
        self.request_obj.save()

        self.object.plan.save()
        set_comment(_(f'Į planą "{self.object.plan}" įtrauktas poreikis "{self.request_obj}".'))
        return redirect(reverse('request-plans', args=[self.request_obj.pk]))


class RequestDeletePlanView(PermissionRequiredMixin, RevisionMixin, DeleteView):
    model = PlanRequest
    template_name = 'confirm_delete.html'

    def has_permission(self):
        request = self.get_object().request
        return has_perm(self.request.user, Action.PLAN, request)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        plan = self.object.plan
        request_obj = self.object.request
        self.object.delete()

        plan.save()
        set_comment(_(f'Iš plano "{plan}" pašalintas poreikis "{request_obj}".'))
        return redirect(reverse('request-plans', args=[request_obj.pk]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.get_object().request
        context['current_title'] = _("Plano pašalinimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('request-list'): _('Poreikiai ir pasiūlymai'),
            reverse('request-detail', args=[request.pk]): request.title,
        }
        return context


class RequestDeletePlanDetailView(RequestDeletePlanView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object().plan.receiver
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[organization.pk]): organization.title,
        }
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        plan = self.object.plan
        request_obj = self.object.request
        self.object.delete()

        plan.save()
        set_comment(_(f'Iš plano "{plan}" pašalintas poreikis "{request_obj}".'))
        return redirect(reverse('plan-detail', args=[plan.receiver.pk, plan.pk]))


class RequestPlansHistoryView(PlanMixin, HistoryView):
    model = Request
    detail_url_name = "request-detail"
    history_url_name = "request-plans-history"
    plan_url_name = 'request-plans'
    tabs_template_name = 'vitrina/requests/tabs.html'

    def get_history_objects(self):
        request_plan_ids = PlanRequest.objects.filter(request=self.object).values_list('plan_id', flat=True)
        return Version.objects.get_for_model(Plan).filter(
            object_id__in=list(request_plan_ids)
        ).order_by('-revision__date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('request-list'): _('Poreikiai ir pasiūlymai'),
            reverse('request-detail', args=[self.object.pk]): self.object.title,
        }
        return context
