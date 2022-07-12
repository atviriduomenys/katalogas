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
    context_object_name = 'dataset'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        dataset = context_data.get('dataset')
        extra_context_data = {
            'tags': dataset.tags.replace(" ", "").split(',') if dataset.tags else "",
            'subscription': [],
            'views': -1,
            'rating': 3.0,
        }
        context_data.update(extra_context_data)
        return context_data
