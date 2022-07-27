from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.db.models import Q

from vitrina.datasets.models import Dataset


class DatasetListView(ListView):
    model = Dataset
    queryset = Dataset.public.order_by('-published')
    template_name = 'vitrina/datasets/list.html'
    paginate_by = 20


class DatasetDetailView(DetailView):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'


class DatasetSearchResultsView(ListView):
    model = Dataset
    template_name = 'vitrina/datasets/list.html'
    paginate_by = 20
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            datasets = Dataset.public.filter(
                Q(title__icontains=query) | Q(title_en__icontains=query)
            )
        else:
            datasets = Dataset.public.order_by('-published')
        return datasets