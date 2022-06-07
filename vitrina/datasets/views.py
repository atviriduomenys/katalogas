from django.views.generic import ListView
from django.views.generic.detail import DetailView

from vitrina.datasets.models import Dataset


class DatasetListView(ListView):
    model = Dataset
    queryset = Dataset.public.order_by('-published')
    template_name = 'vitrina/datasets/list.html'
    paginate_by = 20


class DatasetDetailView(DetailView):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'
