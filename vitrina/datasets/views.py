import csv

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.detail import DetailView
from django.db.models import Q

from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.models import Organization


class DatasetListView(ListView):
    model = Dataset
    template_name = 'vitrina/datasets/list.html'
    paginate_by = 20

    def get_queryset(self):
        datasets = Dataset.public.order_by('-published')
        if self.kwargs.get('slug') and self.request.resolver_match.url_name == 'organization-datasets':
            organization = get_object_or_404(Organization, slug=self.kwargs['slug'])
            datasets = datasets.filter(organization=organization)

        query = self.request.GET.get('q')
        if query:
            datasets = datasets.filter(
                Q(title__icontains=query) | Q(title_en__icontains=query)
            )
        return datasets


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
        dataset_slug = kwargs.get('dataset_slug')
        structure = get_object_or_404(DatasetStructure, dataset__slug=dataset_slug)
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
    def get(self, **kwargs):
        dataset_slug = kwargs.get('dataset_slug')
        structure = get_object_or_404(DatasetStructure, dataset__slug=dataset_slug)
        response = FileResponse(open(structure.file.path, 'rb'))
        return response
