from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.db.models import Q

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Frequency

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
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        filter_dict = self.request.GET.dict()
        datasets = Dataset.public.order_by('-published')

        if query:
            datasets = datasets.filter(
                Q(title__icontains=query) | Q(title_en__icontains=query)
            )
        elif date_from and date_to:
            datasets = datasets.filter(Q(published__gt=date_from) & Q(published__lt=date_to))
        elif date_from:
            datasets = datasets.filter(published__gt=date_from)
        elif date_to:
            datasets = datasets.filter(published__lt=date_to)
        elif filter_dict:
            datasets = datasets.filter(**filter_dict)
        return datasets

    def get_context_data(self, **kwargs):
        context = super(DatasetSearchResultsView, self).get_context_data(**kwargs)
        context['orgs'] = Organization.objects.order_by('title')
        context['categories'] = Category.objects.order_by('title')
        context['frequencies'] = Frequency.objects.order_by('title')
        return context