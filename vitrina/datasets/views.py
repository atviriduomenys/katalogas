from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.db.models import Q

from vitrina.datasets.forms import NewDatasetForm
from vitrina.datasets.models import Dataset
from django import forms


class DatasetListView(ListView):
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
            datasets = Dataset.public.all()
        return datasets.order_by('-published')


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
            'views': -1,
            'rating': 3.0,
            'status': dataset.get_status_display()
        }
        context_data.update(extra_context_data)
        return context_data


class DatasetCreateView(CreateView):
    model = Dataset
    template_name = 'vitrina/templates/base_form.html'
    context_object_name = 'dataset'
    form = NewDatasetForm


class DatasetUpdateView(UpdateView):
    model = Dataset
    template_name = 'vitrina/templates/base_form.html'
    context_object_name = 'dataset'
    form = NewDatasetForm
    fields = ('is_public', 'title', 'description', 'tags',
              'category', 'licence', 'update_frequency',
              'access_rights', 'distribution_conditions')
