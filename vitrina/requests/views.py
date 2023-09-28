from collections import OrderedDict

import numpy as np
import pandas as pd
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, DeleteView
from reversion.models import Version

from vitrina.datasets.forms import PlanForm
from vitrina.orgs.services import has_perm, Action
from reversion import set_comment
from django.db.models import QuerySet, Count, Max, Q, Avg, Sum, Case, When, IntegerField
from reversion.views import RevisionMixin
from vitrina.datasets.models import Dataset, DatasetGroup
from vitrina.classifiers.models import Category
from vitrina.requests.models import Request, Organization, RequestStructure, RequestObject

from vitrina.plans.models import Plan, PlanRequest
from vitrina.requests.forms import RequestForm, RequestPlanForm
from django.core.exceptions import ObjectDoesNotExist
from reversion.views import RevisionMixin
from vitrina.datasets.models import Dataset
from vitrina.requests.models import Request, RequestStructure, RequestObject

from django.utils.translation import gettext_lazy as _

from vitrina.views import HistoryView, HistoryMixin, PlanMixin
from django.contrib import messages
from vitrina.helpers import get_filter_url


def update_request_org_filters(request):
    items = []
    orgs = []
    if request.GET.get('q') and len(request.GET.get('q')) > 2:
        orgs = Organization.objects.distinct().filter(title__icontains=request.GET['q']).annotate(dataset_count=Count(Case(When(dataset__status__in=["HAS_STRUCTURE", "HAS_DATA"], then=1), output_field=IntegerField()))).order_by('-dataset_count')
    else:
        orgs = Organization.objects.distinct().annotate(dataset_count=Count('dataset')).order_by('-dataset_count')[:10]
    for org in orgs:
        items.append({
            'title': org.title,
            'url': get_filter_url(request, 'organization', org.id).strip('q={}'.format(request.GET['q'])),
            'count': org.dataset_count
            })
    return render(request, 'vitrina/datasets/organization_filter_items.html', {'items': items})

def update_request_tag_filters(request):
    items = []
    tags = []
    if request.GET.get('q') and len(request.GET.get('q')) > 2:
        tags = Request.tags.tag_model.objects.distinct().filter(name__icontains=request.GET['q']).annotate(dataset_count=Count(Case(When(dataset__status__in=["HAS_STRUCTURE", "HAS_DATA"], then=1), output_field=IntegerField()))).order_by('-dataset_count')
    else:
        tags = Request.tags.tag_model.objects.distinct().annotate(dataset_count=Count('dataset')).order_by('-dataset_count')[:10]
    for tag in tags:
        items.append({
            'title': tag.name,
            'url': get_filter_url(request, 'tags', tag.id).strip('q={}'.format(request.GET['q'])),
            'count': tag.dataset_count
            })
    return render(request, 'vitrina/datasets/tag_filter_items.html', {'items': items})


class RequestListView(ListView):
    model = Request
    template_name = 'vitrina/requests/list.html'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        queryset = Request.public.all()

        if query:
            queryset = queryset.filter(title__icontains=query)
        if date_from:
            queryset = queryset.filter(created__gte=date_from)
        if date_to:
            queryset = queryset.filter(created__lte=date_to)
        return queryset.order_by("-created")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get("q", "")
        context['selected_date_from'] = self.request.GET.get('date_from')
        context['selected_date_to'] = self.request.GET.get('date_to')
        return context


class RequestPublicationStatsView(RequestListView):
    template_name = 'vitrina/requests/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        requests = self.get_queryset()
        sorting = self.request.GET.get('sort', None)
        year_stats = {}
        for req in requests:
            published = req.created
            if published is not None:
                year_published = published.year
                year_stats[year_published] = year_stats.get(year_published, 0) + 1
        for key, value in year_stats.items():
            if max_count < value:
                max_count = value
        keys = list(year_stats.keys())
        values = list(year_stats.values())
        sorted_value_index = np.argsort(values)
        if sorting is None or sorting == 'sort-year-desc':
            year_stats = OrderedDict(sorted(year_stats.items(), reverse=True))
        elif sorting == 'sort-year-asc':
            year_stats = OrderedDict(sorted(year_stats.items(), reverse=False))
        elif sorting == 'sort-desc':
            year_stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
        elif sorting == 'sort-asc':
            year_stats = {keys[i]: values[i] for i in sorted_value_index}
        context['year_stats'] = year_stats
        context['max_count'] = max_count
        context['filter'] = 'publication'
        context['sort'] = sorting
        return context

class RequestYearStatsView(RequestListView):
    template_name = 'vitrina/requests/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        requests = self.get_queryset()
        sorting = self.request.GET.get('sort', None)
        year_stats = {}
        quarter_stats = {}
        selected_year = str(self.kwargs['year'])
        for req in requests:
            published = req.created
            if published is not None:
                year_published = published.year
                year_stats[year_published] = year_stats.get(year_published, 0) + 1
                quarter = str(year_published) + "-Q" + str(pd.Timestamp(published).quarter)
                quarter_stats[quarter] = quarter_stats.get(quarter, 0) + 1
        for key, value in quarter_stats.items():
            if max_count < value:
                max_count = value
        keys = list(quarter_stats.keys())
        values = list(quarter_stats.values())
        sorted_value_index = np.argsort(values)
        if sorting is None or sorting == 'sort-year-desc':
            quarter_stats = OrderedDict(sorted(quarter_stats.items(), reverse=False))
        elif sorting == 'sort-year-asc':
            quarter_stats = OrderedDict(sorted(quarter_stats.items(), reverse=True))
        elif sorting == 'sort-asc':
            quarter_stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
        elif sorting == 'sort-desc':
            quarter_stats = {keys[i]: values[i] for i in sorted_value_index}
        context['selected_year'] = selected_year
        context['year_stats'] = quarter_stats
        context['max_count'] = max_count
        context['current_object'] = str('year/' + selected_year)
        context['filter'] = 'publication'
        context['sort'] = sorting
        return context


class RequestQuarterStatsView(RequestListView):
    template_name = 'vitrina/requests/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        requests = self.get_queryset()
        sorting = self.request.GET.get('sort', None)
        monthly_stats = {}
        selected_quarter = str(self.kwargs['quarter'])
        for req in requests:
            published = req.created
            if published is not None:
                year_published = published.year
                if str(year_published) in selected_quarter:
                    quarter = str(year_published) + "-Q" + str(pd.Timestamp(published).quarter)
                    if quarter == selected_quarter:
                        month = str(year_published) + "-" + str('%02d' % published.month)
                        monthly_stats[month] = monthly_stats.get(month, 0) + 1
        for m, mv in monthly_stats.items():
            if max_count < mv:
                max_count = mv
        keys = list(monthly_stats.keys())
        values = list(monthly_stats.values())
        sorted_value_index = np.argsort(values)
        if sorting is None or sorting == 'sort-year-desc':
            monthly_stats = OrderedDict(sorted(monthly_stats.items(), reverse=False))
        elif sorting == 'sort-year-asc':
            monthly_stats = OrderedDict(sorted(monthly_stats.items(), reverse=True))
        elif sorting == 'sort-asc':
            monthly_stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
        elif sorting == 'sort-desc':
            monthly_stats = {keys[i]: values[i] for i in sorted_value_index}
        context['selected_quarter'] = self.kwargs['quarter']
        context['year_stats'] = monthly_stats
        context['max_count'] = max_count
        context['current_object'] = str('quarter/' + selected_quarter)
        context['filter'] = 'publication'
        context['sort'] = sorting
        return context


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
            # "related_object": request.object,
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


class RequestDeleteDatasetView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Request
    template_name = 'confirm_remove.html'

    def dispatch(self, request, *args, **kwargs):
        self.request_object = get_object_or_404(Request, pk=self.kwargs.get('pk'))
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get('dataset_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.request_object)

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse('request-datasets', kwargs={'pk': self.dataset.pk}))

    def delete(self, request, *args, **kwargs):
        request_obj_items = RequestObject.objects.filter(object_id=self.dataset.pk,
                                                         content_type=ContentType.objects.get_for_model(self.dataset))
        if len(request_obj_items) > 0:
            for item in request_obj_items:
                item.delete()
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        return reverse('request-datasets', kwargs={'pk': self.request_object.pk})


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


class RequestDatasetView(HistoryMixin, PlanMixin, ListView):
    template_name = 'vitrina/requests/datasets.html'
    detail_url_name = 'request-detail'
    history_url_name = 'request-plans-history'
    plan_url_name = 'request-plans'
    context_object_name = 'datasets'
    paginate_by = 20

    request_obj: Request

    def dispatch(self, request, *args, **kwargs):
        self.request_obj = get_object_or_404(Request, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        request_object_ids = RequestObject.objects.filter(content_type=ContentType.objects.get_for_model(Dataset),
                                                          request_id=self.request_obj.pk) \
            .values_list('object_id', flat=True)
        datasets = Dataset.objects.filter(pk__in=request_object_ids).order_by('-created')
        return datasets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_obj'] = self.request_obj
        # context['datasets'] = datasets
        return context

    def get_plan_object(self):
        return self.request_obj

    def get_detail_object(self):
        return self.request_obj

    def get_history_object(self):
        return self.request_obj
