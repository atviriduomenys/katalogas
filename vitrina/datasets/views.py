from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.db.models import Q
from slugify import slugify

from vitrina.datasets.forms import NewDatasetForm
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


class DatasetCreateView(CreateView):
    model = Dataset
    template_name = 'base_form.html'
    context_object_name = 'dataset'
    form_class = NewDatasetForm

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.organization.slug == self.kwargs['org_slug']:
            return super(DatasetCreateView, self).get(request, *args, **kwargs)
        else:
            return redirect('orgs', self.kwargs['org_slug'])

    def form_valid(self, form):
        object = form.save(commit=False)
        object.slug = slugify(object.title)
        object.save()
        return super(DatasetCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('dataset-detail', kwargs={'slug': self.object.slug})


class DatasetUpdateView(UpdateView):
    model = Dataset
    template_name = 'base_form.html'
    context_object_name = 'dataset'
    form_class = NewDatasetForm

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated and Dataset.objects.filter(manager=self.request.user).exists():
            return super(DatasetUpdateView, self).get(request, *args, **kwargs)
        else:
            return redirect('dataset-detail', self.kwargs['slug'])

    def form_valid(self, form):
        object = form.save(commit=False)
        object.slug = slugify(object.title)
        object.save()
        return super(DatasetUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('dataset-detail', kwargs={'slug': self.object.slug})

