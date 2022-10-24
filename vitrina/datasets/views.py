import csv
import itertools

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import FileResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView, DetailView
from django.views.generic.edit import CreateView, UpdateView

from haystack.generic_views import FacetedSearchView
from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.datasets.forms import DatasetStructureImportForm, DatasetForm
from vitrina.classifiers.models import Category, Frequency
from vitrina.datasets.forms import DatasetSearchForm
from vitrina.datasets.services import update_facet_data
from vitrina.helpers import get_selected_value
from vitrina.orgs.helpers import is_org_dataset_list
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.resources.models import DatasetDistribution
from vitrina.views import HistoryView, HistoryMixin
from vitrina.datasets.structure import detect_read_errors, read


class DatasetListView(FacetedSearchView):
    template_name = 'vitrina/datasets/list.html'
    facet_fields = ['filter_status', 'organization', 'category', 'frequency', 'tags', 'formats']
    form_class = DatasetSearchForm
    paginate_by = 20

    def get_queryset(self):
        datasets = super().get_queryset()
        if is_org_dataset_list(self.request):
            organization = get_object_or_404(
                Organization,
                pk=self.kwargs['pk'],
            )
            datasets = datasets.filter(organization=organization.pk)
        return datasets.order_by('-published')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facet_fields = context.get('facets').get('fields')
        form = context.get('form')
        extra_context = {
            'status_facet': update_facet_data(self.request, facet_fields, 'filter_status',
                                              choices=Dataset.FILTER_STATUSES),
            'organization_facet': update_facet_data(self.request, facet_fields, 'organization', Organization),
            'category_facet': update_facet_data(self.request, facet_fields, 'category', Category),
            'frequency_facet': update_facet_data(self.request, facet_fields, 'frequency', Frequency),
            'tag_facet': update_facet_data(self.request, facet_fields, 'tags'),
            'format_facet': update_facet_data(self.request, facet_fields, 'formats'),
            'selected_status': get_selected_value(form, 'filter_status', is_int=False),
            'selected_organization': get_selected_value(form, 'organization'),
            'selected_categories': get_selected_value(form, 'category', True, False),
            'selected_frequency': get_selected_value(form, 'frequency'),
            'selected_tags': get_selected_value(form, 'tags', True, False),
            'selected_formats': get_selected_value(form, 'formats', True, False),
            'selected_date_from': form.cleaned_data.get('date_from'),
            'selected_date_to': form.cleaned_data.get('date_to'),
        }
        if is_org_dataset_list(self.request):
            # TODO: We get org two times.
            org = get_object_or_404(
                Organization,
                pk=self.kwargs['pk'],
            )
            extra_context['organization'] = org
            extra_context['can_view_members'] = has_perm(
                self.request.user,
                Action.VIEW,
                Representative,
                org
            )
            extra_context['can_create_dataset'] = has_perm(
                self.request.user,
                Action.CREATE,
                Dataset,
                org,
            )
        context.update(extra_context)
        return context


class DatasetDetailView(HistoryMixin, DetailView):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'
    context_object_name = 'dataset'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        dataset = context_data.get('dataset')
        extra_context_data = {
            'tags': dataset.get_tag_list(),
            'subscription': [],
            'status': dataset.get_status_display(),
            'can_add_resource': has_perm(self.request.user, Action.CREATE, DatasetDistribution),
            'can_update_dataset': has_perm(self.request.user, Action.UPDATE, dataset),
            'can_view_members': has_perm(self.request.user, Action.VIEW, Representative, dataset),
            'resources': dataset.datasetdistribution_set.all(),
        }
        context_data.update(extra_context_data)
        return context_data


class DatasetDistributionDownloadView(View):
    def get(self, request, dataset_id, distribution_id, file):
        distribution = get_object_or_404(
            DatasetDistribution,
            dataset__pk=dataset_id,
            pk=distribution_id,
            file__icontains=file
        )
        response = FileResponse(open(distribution.file.path, 'rb'))
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
            rows = open(distribution.file.path, encoding='utf-8')
            rows = itertools.islice(rows, 100)
            data = list(csv.reader(rows, delimiter=";"))
        return JsonResponse({'data': data})


class DatasetStructureView(TemplateView):
    template_name = 'vitrina/datasets/structure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        structure = dataset.current_structure
        context['errors'] = []
        context['manifest'] = None
        if structure and structure.file:
            if errors := detect_read_errors(structure.file.path):
                context['errors'] = errors
            else:
                with open(
                    structure.file.path,
                    encoding='utf-8',
                    errors='replace',
                ) as f:
                    reader = csv.DictReader(f)
                    state = read(reader)
                context['errors'] = state.errors
                context['manifest'] = state.manifest
        return context


class DatasetStructureDownloadView(View):
    def get(self, request, pk):
        dataset = get_object_or_404(Dataset, pk=pk)
        structure = dataset.current_structure
        response = FileResponse(open(structure.file.path, 'rb'))
        return response


class DatasetCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    CreateView
):
    model = Dataset
    template_name = 'base_form.html'
    context_object_name = 'dataset'
    form_class = DatasetForm

    def has_permission(self):
        organization = get_object_or_404(Organization, id=self.kwargs.get('pk'))
        return has_perm(self.request.user, Action.CREATE, Dataset, organization)

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
        self.object = form.save(commit=False)
        self.object.slug = slugify(self.object.title)
        self.object.organization_id = self.kwargs.get('pk')
        self.object.save()
        set_comment(Dataset.CREATED)
        return HttpResponseRedirect(self.get_success_url())


class DatasetUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Dataset
    template_name = 'base_form.html'
    context_object_name = 'dataset'
    form_class = DatasetForm

    def has_permission(self):
        dataset = get_object_or_404(Dataset, id=self.kwargs['pk'])
        return has_perm(self.request.user, Action.UPDATE, dataset)

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
        self.object = form.save(commit=False)
        self.object.slug = slugify(self.object.title)
        self.object.save()
        set_comment(Dataset.EDITED)
        return HttpResponseRedirect(self.get_success_url())


class DatasetHistoryView(HistoryView):
    model = Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_view_members'] = has_perm(self.request.user, Action.VIEW, Representative, context)
        return context


class DatasetStructureImportView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = DatasetStructure
    form_class = DatasetStructureImportForm
    template_name = 'base_form.html'

    dataset: Dataset | None = None

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.CREATE,
            DatasetStructure,
            self.dataset,
        )

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            'current_title': _("Struktūros importas"),
            'parent_title': self.dataset.title,
            'parent_url': self.dataset.get_absolute_url(),
        }

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.dataset = self.dataset
        self.object.save()
        self.object.dataset.current_structure = self.object
        self.object.dataset.save()
        return HttpResponseRedirect(self.get_success_url())


class DatasetMembersView(LoginRequiredMixin, PermissionRequiredMixin, DatasetDetailView):
    template_name = 'vitrina/datasets/members_list.html'
    paginate_by = 20

    def has_permission(self):
        dataset = get_object_or_404(Dataset, pk=self.kwargs.get('pk'))
        return has_perm(self.request.user, Action.VIEW, Representative, dataset)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        else:
            dataset = get_object_or_404(Dataset, id=self.kwargs['pk'])
            return redirect(dataset)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        dataset: Dataset = self.object
        context_data['members'] = Representative.objects.filter(content_type=ContentType.objects.get_for_model(Dataset),
                                                                object_id=dataset.pk).order_by("role",
                                                                                               "first_name",
                                                                                               'last_name')
        context_data['can_view_members'] = has_perm(self.request.user, Action.VIEW, Representative, dataset)
        return context_data
