import csv

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from haystack.generic_views import FacetedSearchView

from vitrina.datasets.forms import DatasetSearchForm
from vitrina.helpers import get_selected_value
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.datasets.services import update_facet_data
from vitrina.orgs.models import Organization
from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Frequency


class DatasetListView(FacetedSearchView):
    template_name = 'vitrina/datasets/list.html'
    facet_fields = ['filter_status', 'organization', 'category', 'frequency', 'tags', 'formats']
    form_class = DatasetSearchForm

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.order_by('-published')

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
        context.update(extra_context)
        return context


class DatasetDetailView(DetailView):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'
    context_object_name = 'dataset'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        dataset = context_data.get('dataset')
        extra_context_data = {
            'tags': dataset.get_tag_list(),
            'subscription': [],
            'rating': 3.0,
            'status': dataset.get_status_display()
        }
        context_data.update(extra_context_data)
        return context_data


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
