from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.views.generic.detail import DetailView

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization


class DatasetListView(ListView):
    model = Dataset
    template_name = 'vitrina/datasets/list.html'
    paginate_by = 20

    def get_queryset(self):
        datasets = Dataset.public.order_by('-published')
        if self.kwargs.get('slug') and self.request.resolver_match.url_name == 'organization-datasets':
            organization = get_object_or_404(Organization, slug=self.kwargs['slug'])
            datasets = Dataset.public.filter(organization=organization)
        return datasets


class DatasetDetailView(DetailView):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'
