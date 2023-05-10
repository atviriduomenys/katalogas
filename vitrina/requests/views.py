from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from vitrina.requests.forms import RequestSearchForm
from vitrina.orgs.services import has_perm, Action
from vitrina.orgs.helpers import is_org_dataset_list
from vitrina.helpers import get_selected_value
from reversion import set_comment
from vitrina.datasets.services import update_facet_data
from haystack.generic_views import FacetedSearchView
from vitrina.requests.forms import RequestForm
from django.core.exceptions import ObjectDoesNotExist
from reversion.views import RevisionMixin
from vitrina.datasets.models import Dataset, DatasetGroup
from vitrina.classifiers.models import Category, Frequency
from vitrina.requests.models import Request, Organization, RequestStructure

from django.utils.translation import gettext_lazy as _

from vitrina.views import HistoryView, HistoryMixin


class RequestListView(FacetedSearchView):
    template_name = 'vitrina/requests/list.html'
    facet_fields = ['filter_status', 'organization', 'category', 'parent_category', 'groups', 'tags']
    facet_limit = 100
    paginate_by = 20
    form_class = RequestSearchForm
    
    def get_queryset(self):
        requests = super().get_queryset()
        return requests.order_by('-created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facet_fields = context.get('facets').get('fields')
        form = context.get('form')
        extra_context = {
            'status_facet': update_facet_data(self.request, facet_fields, 'filter_status',
                                              choices=Dataset.FILTER_STATUSES),
            'organization_facet': update_facet_data(self.request, facet_fields, 'organization', Organization),
            'category_facet': update_facet_data(self.request, facet_fields, 'category', Category),
            'parent_category_facet': update_facet_data(self.request, facet_fields, 'parent_category', Category),
            'group_facet': update_facet_data(self.request, facet_fields, 'groups', DatasetGroup),
            'tag_facet': update_facet_data(self.request, facet_fields, 'tags'),
            'selected_status': get_selected_value(form, 'filter_status', is_int=False),
            'selected_organization': get_selected_value(form, 'organization'),
            'selected_categories': get_selected_value(form, 'category', True, False),
            'selected_parent_category': get_selected_value(form, 'parent_category', True, False),
            'selected_groups': get_selected_value(form, 'groups', True, False),
            'selected_tags': get_selected_value(form, 'tags', True, False),
            'selected_date_from': form.cleaned_data.get('date_from'),
            'selected_date_to': form.cleaned_data.get('date_to'),
        }     
        context.update(extra_context)
        return context

class RequestDetailView(HistoryMixin, DetailView):
    model = Request
    template_name = 'vitrina/requests/detail.html'
    context_object_name = 'request_object'
    detail_url_name = 'request-detail'
    history_url_name = 'request-history'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        request: Request = self.object
        dataset = None
        if request.dataset:
            try:
                dataset = request.dataset
            except ObjectDoesNotExist:
                pass

        extra_context_data = {
            "formats": request.format.replace(" ", "").split(",") if request.format else [],
            "changes": request.changes.replace(" ", "").split(",") if request.changes else [],
            "purposes": request.purpose.replace(" ", "").split(",") if request.purpose else [],
            "structure": RequestStructure.objects.filter(request_id=request.pk),
            "dataset": dataset,
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


class RequestHistoryView(HistoryView):
    model = Request
    detail_url_name = "request-detail"
    history_url_name = "request-history"
    tabs_template_name = 'component/tabs.html'
