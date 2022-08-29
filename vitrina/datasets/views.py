from django.core.exceptions import ObjectDoesNotExist
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
        organization = None
        if self.kwargs.get('slug'):
            try:
                organization = Organization.objects.get(slug=self.kwargs['slug'])
            except ObjectDoesNotExist:
                pass
        if organization:
            datasets = Dataset.public.filter(organization=organization)
        return datasets


class DatasetDetailView(DetailView):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'
