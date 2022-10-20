import csv
import itertools

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from django.views import View
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from haystack.generic_views import FacetedSearchView

from parler.views import TranslatableUpdateView, TranslatableCreateView, LanguageChoiceMixin
from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Frequency
from vitrina.datasets.forms import NewDatasetForm
from vitrina.datasets.forms import DatasetSearchForm
from vitrina.helpers import get_selected_value
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.datasets.services import update_facet_data
from vitrina.orgs.helpers import is_org_dataset_list
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.resources.models import DatasetDistribution


class DatasetListView(FacetedSearchView):
    template_name = 'vitrina/datasets/list.html'
    facet_fields = ['filter_status', 'organization', 'category', 'frequency', 'tags', 'formats']
    form_class = DatasetSearchForm
    paginate_by = 20

    def get_queryset(self):
        datasets = super().get_queryset()
        if is_org_dataset_list(self.request):
            organization = get_object_or_404(
                Organization,
                pk=self.kwargs['pk'],
            )
            datasets = datasets.filter(organization=organization.pk)
        return datasets.order_by('-published')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facet_fields = context.get('facets').get('fields')
        form = context.get('form')
        extra_context = {
            'status_facet': update_facet_data(self.request, facet_fields, 'filter_status',
                                              choices=Dataset.FILTER_STATUSES),
            'organization_facet': update_facet_data(self.request, facet_fields, 'organization', Organization),
            'category_facet': update_facet_data(self.request, facet_fields, 'category', Category),
            'frequency_facet': update_facet_data(self.request, facet_fields, 'frequency', Frequency),
            'tag_facet': update_facet_data(self.request, facet_fields, 'tags'),
            'format_facet': update_facet_data(self.request, facet_fields, 'formats'),
            'selected_status': get_selected_value(form, 'filter_status', is_int=False),
            'selected_organization': get_selected_value(form, 'organization'),
            'selected_categories': get_selected_value(form, 'category', True, False),
            'selected_frequency': get_selected_value(form, 'frequency'),
            'selected_tags': get_selected_value(form, 'tags', True, False),
            'selected_formats': get_selected_value(form, 'formats', True, False),
            'selected_date_from': form.cleaned_data.get('date_from'),
            'selected_date_to': form.cleaned_data.get('date_to'),
        }
        if is_org_dataset_list(self.request):
            # TODO: We get org two times.
            org = get_object_or_404(
                Organization,
                pk=self.kwargs['pk'],
            )
            extra_context['organization'] = org
            extra_context['can_view_members'] = has_perm(
                self.request.user,
                Action.VIEW,
                Representative,
                org
            )
            extra_context['can_create_dataset'] = has_perm(
                self.request.user,
                Action.CREATE,
                Dataset,
                org,
            )
        context.update(extra_context)
        return context


class DatasetDetailView(LanguageChoiceMixin, DetailView):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'
    context_object_name = 'dataset'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        dataset = context_data.get('dataset')
        extra_context_data = {
            'tags': dataset.get_tag_list(),
            'subscription': [],
            'status': dataset.get_status_display(),
            'can_update_dataset': has_perm(self.request.user, Action.UPDATE, dataset),
            'resources': dataset.datasetdistribution_set.all(),
        }
        context_data.update(extra_context_data)
        return context_data


class DatasetDistributionDownloadView(View):
    def get(self, request, dataset_id, distribution_id, filename):
        distribution = get_object_or_404(
            DatasetDistribution,
            dataset__pk=dataset_id,
            pk=distribution_id,
            filename__icontains=filename
        )
        response = FileResponse(open(distribution.filename.path, 'rb'))
        return response


class DatasetDistributionPreviewView(View):
    def get(self, request, dataset_id, distribution_id):
        distribution = get_object_or_404(
            DatasetDistribution,
            dataset__pk=dataset_id,
            pk=distribution_id
        )
        data = []
        if distribution.is_previewable():
            rows = open(distribution.filename.path, encoding='utf-8')
            rows = itertools.islice(rows, 100)
            data = list(csv.reader(rows, delimiter=";"))
        return JsonResponse({'data': data})


class DatasetStructureView(TemplateView):
    template_name = 'vitrina/datasets/structure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset_id = kwargs.get('pk')
        structure = get_object_or_404(DatasetStructure, dataset__pk=dataset_id)
        data = []
        can_show = True
        if structure and structure.file:
            try:
                data = list(csv.reader(open(structure.file.path, encoding='utf-8'), delimiter=";"))
            except BaseException:
                can_show = False
        context['can_show'] = can_show
        context['structure_data'] = data
        return context


class DatasetStructureDownloadView(View):
    def get(self, request, pk):
        structure = get_object_or_404(DatasetStructure, dataset__pk=pk)
        response = FileResponse(open(structure.file.path, 'rb'))
        return response


class DatasetCreateView(LoginRequiredMixin, PermissionRequiredMixin, TranslatableCreateView, LanguageChoiceMixin):
    model = Dataset
    template_name = 'base_form.html'
    context_object_name = 'dataset'
    form_class = NewDatasetForm

    def has_permission(self):
        organization = get_object_or_404(Organization, id=self.kwargs.get('pk'))
        return has_perm(self.request.user, Action.CREATE, Dataset, organization)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            org = get_object_or_404(Organization, id=self.kwargs['pk'])
            return redirect(org)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Naujas duomenų rinkinys')
        return context

    def get(self, request, *args, **kwargs):
        return super(DatasetCreateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        object = form.save(commit=False)
        object.slug = slugify(object.title)
        object.organization_id = self.kwargs.get('pk')
        return super().form_valid(form)


class DatasetUpdateView(LoginRequiredMixin, PermissionRequiredMixin, TranslatableUpdateView):
    model = Dataset
    template_name = 'base_form.html'
    context_object_name = 'dataset'
    form_class = NewDatasetForm

    def has_permission(self):
        dataset = get_object_or_404(Dataset, id=self.kwargs['pk'])
        return has_perm(self.request.user, Action.UPDATE, dataset)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            dataset = get_object_or_404(Dataset, id=self.kwargs['pk'])
            return redirect(dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Duomenų rinkinio redagavimas')
        return context

    def get(self, request, *args, **kwargs):
        return super(DatasetUpdateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        object = form.save(commit=False)
        object.slug = slugify(object.title)
        return super().form_valid(form)
