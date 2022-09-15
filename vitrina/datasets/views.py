from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView
import csv

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.db.models import Q
from slugify import slugify

from vitrina import settings
from vitrina.datasets.forms import NewDatasetForm
from vitrina.datasets.models import Dataset
from vitrina.datasets.forms import DatasetFilterForm
from vitrina.helpers import get_selected_value, get_filter_url
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.datasets.services import filter_by_status, get_related_categories, get_tag_list, get_related_tag_list, \
    get_category_counts
from vitrina.orgs.models import Organization
from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Frequency
from django.http import HttpResponseBadRequest

from django.utils.translation import gettext_lazy as _


class DatasetListView(ListView):
    model = Dataset
    template_name = 'vitrina/datasets/list.html'
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        filter_form = DatasetFilterForm(self.request.GET)
        if filter_form.is_valid():
            return super().get(request, *args, **kwargs)
        return HttpResponseBadRequest(_("Klaida"))

    def get_queryset(self):
        datasets = Dataset.public.order_by('-published')
        if self.kwargs.get('slug') and self.request.resolver_match.url_name == 'organization-datasets':
            organization = get_object_or_404(Organization, slug=self.kwargs['slug'])
            datasets = datasets.filter(organization=organization)

        filter_form = DatasetFilterForm(self.request.GET)
        filter_form.is_valid()
        cleaned_data = filter_form.cleaned_data

        query = cleaned_data.get('q')
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        status = cleaned_data.get('status')
        tags = cleaned_data.get('tags')
        category = cleaned_data.get('category')
        organization = cleaned_data.get('organization')
        frequency = cleaned_data.get('frequency')

        if query:
            datasets = datasets.filter(
                Q(title__icontains=query) | Q(title_en__icontains=query)
            )
        if date_from and date_to:
            datasets = datasets.filter(published__range=(date_from, date_to))
        elif date_from:
            datasets = datasets.filter(published__gte=date_from)
        elif date_to:
            datasets = datasets.filter(published__lte=date_to)
        if status:
            datasets = filter_by_status(datasets, status)
        for tag in tags:
            datasets = datasets.filter(tags__icontains=tag)
        if category:
            related_categories = get_related_categories(category, only_children=True)
            datasets = datasets.filter(category__pk__in=related_categories)
        if organization:
            datasets = datasets.filter(organization=organization)
        if frequency:
            datasets = datasets.filter(frequency=frequency)
        return datasets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_queryset = self.get_queryset()

        selected_status = get_selected_value(self.request, 'status', is_int=False)
        selected_organization = get_selected_value(self.request, 'organization')
        selected_categories = get_selected_value(self.request, 'category', multiple=True)
        selected_frequency = get_selected_value(self.request, 'frequency')
        selected_tags = get_selected_value(self.request, 'tags', multiple=True, is_int=False)
        selected_date_from = get_selected_value(self.request, 'date_from', is_int=False)
        selected_date_to = get_selected_value(self.request, 'date_to', is_int=False)

        related_categories = get_related_categories(selected_categories)
        tag_list = get_tag_list()
        related_tag_list = get_related_tag_list(selected_tags, filtered_queryset)
        category_counts = get_category_counts(selected_categories, related_categories, filtered_queryset)

        status_counts = {}
        for status in Dataset.FILTER_STATUSES.keys():
            status_counts[status] = filter_by_status(filtered_queryset, status).count()

        search_form_params = {}
        if selected_status:
            search_form_params['status'] = [selected_status]
        if selected_organization:
            search_form_params['organization'] = [selected_organization]
        if selected_categories:
            search_form_params['category'] = selected_categories
        if selected_tags:
            search_form_params['tags'] = selected_tags
        if selected_frequency:
            search_form_params['frequency'] = [selected_frequency]
        if selected_date_from:
            search_form_params['date_from'] = [selected_date_from]
        if selected_date_to:
            search_form_params['date_to'] = [selected_date_to]

        extra_context = {
            'num_found': filtered_queryset.count(),
            'status_filters': [{
                'key': key,
                'title': value,
                'query': get_filter_url(self.request, 'status', key),
                'count': status_counts.get(key, 0)
            } for key, value in Dataset.FILTER_STATUSES.items() if status_counts.get(key, 0) > 0],
            'selected_status': selected_status,

            'organization_filters': [{
                'id': org.pk,
                'title': org.title,
                'query': get_filter_url(self.request, 'organization', org.pk),
                'count': filtered_queryset.filter(organization=org).count()
            } for org in Organization.objects.order_by('title')
                if filtered_queryset.filter(organization=org).count() > 0],
            'selected_organization': selected_organization,

            'category_filters': [{
                'id': category.pk,
                'title': category.title,
                'query': get_filter_url(self.request, 'category', category.pk, True),
                'count': category_counts.get(category.pk, 0)
            } for category in Category.objects.order_by('title') if category_counts.get(category.pk, 0) > 0],
            'selected_categories': selected_categories,
            'related_categories': related_categories,

            'frequency_filters': [{
                'id': frequency.pk,
                'title': frequency.title,
                'query': get_filter_url(self.request, 'frequency', frequency.pk),
                'count': filtered_queryset.filter(frequency=frequency).count()
            } for frequency in Frequency.objects.order_by('title')
                if filtered_queryset.filter(frequency=frequency).count() > 0],
            'selected_frequency': selected_frequency,

            'tag_filters': [{
                'title': tag,
                'query': get_filter_url(self.request, 'tags', tag, True),
                'count': filtered_queryset.filter(tags__icontains=tag).count()
            } for tag in tag_list if filtered_queryset.filter(tags__icontains=tag).count() > 0],
            'selected_tags': selected_tags,
            'related_tags': related_tag_list,

            'selected_date_from': selected_date_from,
            'selected_date_to': selected_date_to,
            'search_form_params': search_form_params.items()
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


class DatasetCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Dataset
    template_name = 'base_form.html'
    context_object_name = 'dataset'
    form_class = NewDatasetForm

    def has_permission(self):
        if self.request.user.organization:
            return self.request.user.organization.slug == self.kwargs['slug']
        else:
            return False

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            org = get_object_or_404(Organization, kind=self.kwargs['org_kind'], slug=self.kwargs['slug'])
            return redirect(org)

    def get(self, request, *args, **kwargs):
        return super(DatasetCreateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        object = form.save(commit=False)
        object.slug = slugify(object.title)
        return super().form_valid(form)


class DatasetUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Dataset
    template_name = 'base_form.html'
    context_object_name = 'dataset'
    form_class = NewDatasetForm

    def has_permission(self):
        if self.request.user.organization:
            dataset = Dataset.objects.filter(slug=self.kwargs['slug'])
            if self.request.user.organization.slug == self.kwargs['org_slug'] or dataset.manager == self.request.user:
                return True
            else:
                return False
        else:
            return False

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            dataset = get_object_or_404(Dataset, slug=self.kwargs['slug'])
            return redirect(dataset)

    def get(self, request, *args, **kwargs):
        return super(DatasetUpdateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        object = form.save(commit=False)
        object.slug = slugify(object.title)
        return super().form_valid(form)


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
    def get(self, request, organization_kind, organization_slug, dataset_slug):
        structure = get_object_or_404(
            DatasetStructure,
            dataset__organization__kind=organization_kind,
            dataset__organization__slug=organization_slug,
            dataset__slug=dataset_slug,
        )
        response = FileResponse(open(structure.file.path, 'rb'))
        return response
