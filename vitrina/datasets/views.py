from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
import itertools
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
import csv
from django.views import View
from django.views.generic import ListView, TemplateView
from django.shortcuts import redirect
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.db.models import Q
from slugify import slugify
from vitrina import settings
from vitrina.datasets.forms import NewDatasetForm
from vitrina.datasets.forms import DatasetFilterForm
from vitrina.helpers import get_selected_value, get_filter_url
from vitrina.datasets.models import Dataset, DatasetStructure, DatasetMember
from vitrina.datasets.services import filter_by_status, get_related_categories, get_tag_list, get_related_tag_list, \
    get_category_counts, can_update_dataset, can_create_dataset, can_see_dataset_members
from vitrina.orgs.models import Organization
from vitrina.classifiers.models import Category
from vitrina.classifiers.models import Frequency
from django.http import HttpResponseBadRequest, FileResponse

from django.utils.translation import gettext_lazy as _

from vitrina.resources.models import DatasetDistribution


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
        if self.kwargs.get('pk') and self.request.resolver_match.url_name == 'organization-datasets':
            organization = get_object_or_404(Organization, pk=self.kwargs['pk'])
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
            'search_form_params': search_form_params.items(),
            'can_create_dataset': can_create_dataset(self.request.user, self.kwargs.get('pk'))
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
            'status': dataset.get_status_display(),
            'can_update_dataset': can_update_dataset(self.request.user, dataset),
            'resources': dataset.datasetdistribution_set.all(),
        }
        context_data.update(extra_context_data)
        return context_data


class DatasetDistributionDownloadView(View):
    def get(self, request, dataset_id, distribution_id, filename):
        distribution = get_object_or_404(
            DatasetDistribution,
            dataset__pk=dataset_id,
            pk=distribution_id,
            filename__icontains=filename
        )
        response = FileResponse(open(distribution.filename.path, 'rb'))
        return response


class DatasetDistributionPreviewView(View):
    def get(self, request, dataset_id, distribution_id):
        distribution = get_object_or_404(
            DatasetDistribution,
            dataset__pk=dataset_id,
            pk=distribution_id
        )
        data = []
        if distribution.is_previewable():
            rows = open(distribution.filename.path, encoding='utf-8')
            rows = itertools.islice(rows, 100)
            data = list(csv.reader(rows, delimiter=";"))
        return JsonResponse({'data': data})


class DatasetStructureView(TemplateView):
    template_name = 'vitrina/datasets/structure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset_id = kwargs.get('pk')
        structure = get_object_or_404(DatasetStructure, dataset__pk=dataset_id)
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
    def get(self, request, pk):
        structure = get_object_or_404(DatasetStructure, dataset__pk=pk)
        response = FileResponse(open(structure.file.path, 'rb'))
        return response


class DatasetCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Dataset
    template_name = 'base_form.html'
    context_object_name = 'dataset'
    form_class = NewDatasetForm

    def has_permission(self):
        return can_create_dataset(self.request.user, self.kwargs['pk'])

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            org = get_object_or_404(Organization, id=self.kwargs['pk'])
            return redirect(org)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Naujas duomenų rinkinys')
        return context

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
        dataset = get_object_or_404(Dataset, id=self.kwargs['pk'])
        return can_update_dataset(self.request.user, dataset)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            dataset = get_object_or_404(Dataset, id=self.kwargs['pk'])
            return redirect(dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Duomenų rinkinio redagavimas')
        return context

    def get(self, request, *args, **kwargs):
        return super(DatasetUpdateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        object = form.save(commit=False)
        object.slug = slugify(object.title)
        return super().form_valid(form)


class DatasetMembersView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    login_url = settings.LOGIN_URL
    model = DatasetMember
    template_name = 'vitrina/datasets/members_list.html'
    context_object_name = 'dataset_members'
    paginate_by = 20

    def has_permission(self):
        dataset = Dataset.public.get_from_url_args(**self.kwargs)
        return can_see_dataset_members(self.request.user, dataset)

    def get_queryset(self):
        dataset = Dataset.public.get_from_url_args(**self.kwargs)
        return dataset.datasetmember_set.all()
