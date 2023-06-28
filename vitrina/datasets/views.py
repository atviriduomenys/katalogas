import csv
import itertools
import json
import secrets

import pandas as pd
import numpy as np

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import QuerySet, Count, Max
from django.db.models.functions import ExtractYear, ExtractMonth
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.template.defaultfilters import date as _date

from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail

from haystack.generic_views import FacetedSearchView
from parler.utils.context import switch_language
from parler.utils.i18n import get_language
from itsdangerous import URLSafeSerializer
from reversion import set_comment
from reversion.views import RevisionMixin

from parler.views import TranslatableUpdateView, TranslatableCreateView, LanguageChoiceMixin, ViewUrlMixin

from vitrina.api.models import ApiKey
from vitrina.projects.models import Project
from vitrina.comments.models import Comment
from vitrina.settings import ELASTIC_FACET_SIZE
from vitrina.structure.services import create_structure_objects
from vitrina.structure.views import DatasetStructureMixin
from vitrina.views import HistoryView, HistoryMixin
from vitrina.datasets.forms import DatasetStructureImportForm, DatasetForm, DatasetSearchForm, AddProjectForm, \
    DatasetCategoryForm
from vitrina.datasets.forms import DatasetMemberUpdateForm, DatasetMemberCreateForm
from vitrina.datasets.services import update_facet_data, get_projects
from vitrina.datasets.models import Dataset, DatasetStructure, DatasetGroup
from vitrina.datasets.structure import detect_read_errors, read
from vitrina.classifiers.models import Category, Frequency
from vitrina.helpers import get_selected_value
from vitrina.orgs.helpers import is_org_dataset_list
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.resources.models import DatasetDistribution
from vitrina.users.models import User
from vitrina.helpers import get_current_domain
from datetime import datetime
import pytz

class DatasetListView(FacetedSearchView):
    template_name = 'vitrina/datasets/list.html'
    facet_fields = [
        'filter_status',
        'organization',
        'jurisdiction',
        'category',
        'parent_category',
        'groups',
        'frequency',
        'tags',
        'formats',
        'published',
        'level'
    ]
    form_class = DatasetSearchForm
    max_num_facets = 20
    paginate_by = 20

    def get_queryset(self):
        datasets = super().get_queryset()

        options = {"size": ELASTIC_FACET_SIZE}
        for field in self.facet_fields:
            datasets = datasets.facet(field, **options)

        if is_org_dataset_list(self.request):
            self.organization = get_object_or_404(
                Organization,
                pk=self.kwargs['pk'],
            )
            datasets = datasets.filter(organization=self.organization.pk)
        return datasets.order_by('-published')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        datasets = self.get_queryset()
        facet_fields = context.get('facets').get('fields')
        form = context.get('form')
        extra_context = {
            'status_facet': update_facet_data(self.request, facet_fields, 'filter_status',
                                              choices=Dataset.FILTER_STATUSES),
            'jurisdiction_facet': update_facet_data(self.request, facet_fields, 'jurisdiction', Organization),
            'organization_facet': update_facet_data(self.request, facet_fields, 'organization', Organization),
            'category_facet': update_facet_data(self.request, facet_fields, 'category', Category),
            'parent_category_facet': update_facet_data(self.request, facet_fields, 'parent_category', Category),
            'group_facet': update_facet_data(self.request, facet_fields, 'groups', DatasetGroup),
            'frequency_facet': update_facet_data(self.request, facet_fields, 'frequency', Frequency),
            'tag_facet': update_facet_data(self.request, facet_fields, 'tags'),
            'format_facet': update_facet_data(self.request, facet_fields, 'formats'),
            'published_facet': update_facet_data(self.request, facet_fields, 'published'),
            'level_facet': update_facet_data(self.request, facet_fields, 'level'),
            'selected_status': get_selected_value(form, 'filter_status', is_int=False),
            'selected_jurisdiction': get_selected_value(form, 'jurisdiction', True, False),
            'selected_organization': get_selected_value(form, 'organization', True, False),
            'selected_categories': get_selected_value(form, 'category', True, False),
            'selected_parent_category': get_selected_value(form, 'parent_category', True, False),
            'selected_groups': get_selected_value(form, 'groups', True, False),
            'selected_frequency': get_selected_value(form, 'frequency'),
            'selected_tags': get_selected_value(form, 'tags', True, False),
            'selected_formats': get_selected_value(form, 'formats', True, False),
            'selected_date_from': form.cleaned_data.get('date_from'),
            'selected_date_to': form.cleaned_data.get('date_to'),
            'selected_level': get_selected_value(form, 'level'),
        }
        yearly_stats = {}
        quarter_stats = {}
        monthly_stats = {}
        for d in datasets:
            published = d.published
            if published is not None:
                year_published = published.year
                yearly_stats[year_published] = yearly_stats.get(year_published, 0) + 1
                quarter = str(year_published) + "-Q" + str(pd.Timestamp(published).quarter)
                quarter_stats[quarter] = quarter_stats.get(quarter, 0) + 1
                month = str(year_published) + "-" + str('%02d' % published.month)
                monthly_stats[month] = monthly_stats.get(month, 0) + 1
        final = {}
        months = {}

        for key, value in yearly_stats.items():
            final[key] = {}
            final[key]['total'] = value
            final[key]['quarters'] = {}
            final[key]['months'] = {}
            for qk, qv in quarter_stats.items():
                if qk.startswith(str(key)):
                    final[key]['quarters'][qk] = qv

        for q, qv in quarter_stats.items():
            y_index = int(q.split('-Q')[0])
            q_index = int(q.split('-Q')[1])
            qq = {q: qv}
            q_months = {}
            for m, mv in monthly_stats.items():
                y = int(m.split('-')[0])
                m_index = m.split('-')[1]
                m_q = (int(m_index) - 1) // 3 + 1
                if q_index == m_q and y_index == y:
                    q_months[m] = mv
                    qq = q_months
            months[q] = qq

        if is_org_dataset_list(self.request):
            extra_context['organization'] = self.organization
            extra_context['can_view_members'] = has_perm(
                self.request.user,
                Action.VIEW,
                Representative,
                self.organization
            )
            extra_context['can_create_dataset'] = has_perm(
                self.request.user,
                Action.CREATE,
                Dataset,
                self.organization,
            )
        context.update(extra_context)
        context['year_filter'] = final
        context['months'] = months
        return context


class DatasetDetailView(
    LanguageChoiceMixin,
    HistoryMixin,
    DatasetStructureMixin,
    DetailView
):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'
    context_object_name = 'dataset'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        dataset = context_data.get('dataset')
        organization = get_object_or_404(Organization, id=dataset.organization.pk)
        extra_context_data = {
            'tags': dataset.get_tag_list(),
            'subscription': [],
            'status': dataset.get_status_display(),
            #TODO: harvested functionality needs to be implemented
            'harvested': '',
            'can_add_resource': has_perm(self.request.user, Action.CREATE, DatasetDistribution),
            'can_update_dataset': has_perm(self.request.user, Action.UPDATE, dataset),
            'can_view_members': has_perm(self.request.user, Action.VIEW, Representative, dataset),
            'resources': dataset.datasetdistribution_set.all(),
            'org_logo': organization.image,
        }
        context_data.update(extra_context_data)
        return context_data


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
        context['structure'] = structure
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


class DatasetCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    TranslatableCreateView,
    LanguageChoiceMixin
):
    model = Dataset
    template_name = 'vitrina/datasets/form.html'
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
        self.object = form.save(commit=True)
        self.object.slug = slugify(self.object.title)
        self.object.organization_id = self.kwargs.get('pk')
        self.object.save()
        set_comment(Dataset.CREATED)
        return HttpResponseRedirect(self.get_success_url())


class DatasetUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    TranslatableUpdateView,
    ViewUrlMixin
):
    model = Dataset
    template_name = 'vitrina/datasets/form.html'
    view_url_name = 'dataset:edit'
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
        switch_language(self.object, get_language())
        return context

    def get(self, request, *args, **kwargs):
        return super(DatasetUpdateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.slug = slugify(self.object.title)
        tags = form.cleaned_data['tags']
        self.object.tags.set(tags)
        self.object.save()
        set_comment(Dataset.EDITED)
        return HttpResponseRedirect(self.get_success_url())


class DatasetHistoryView(DatasetStructureMixin, HistoryView):
    model = Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    tabs_template_name = 'vitrina/datasets/tabs.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
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
        create_structure_objects(self.object)
        return HttpResponseRedirect(self.get_success_url())


class DatasetMembersView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    HistoryMixin,
    DatasetStructureMixin,
    ListView,
):
    model = Representative
    template_name = 'vitrina/datasets/members_list.html'
    context_object_name = 'members'
    paginate_by = 20

    # HistroyMixin
    object: Dataset
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )

    def get_queryset(self):
        return (
            Representative.objects.
            filter(
                content_type=ContentType.objects.get_for_model(Dataset),
                object_id=self.object.pk,
            ).
            order_by("role", "first_name", 'last_name')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.object
        context['has_permission'] = has_perm(
            self.request.user,
            Action.CREATE,
            Representative,
            self.object,
        )
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        return context


class CreateMemberView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Representative
    form_class = DatasetMemberCreateForm
    template_name = 'base_form.html'

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs['dataset_id'])
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.CREATE,
            Representative,
            self.dataset,
        )

    def get_success_url(self):
        return reverse('dataset-members', kwargs={
            'pk': self.dataset.pk,
        })

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['object_id'] = self.dataset.pk
        return kwargs

    def form_valid(self, form):
        self.object: Representative = form.save(commit=False)
        self.object.content_type = ContentType.objects.get_for_model(Dataset)
        self.object.object_id = self.dataset.id
        try:
            user = User.objects.get(email=self.object.email)
        except ObjectDoesNotExist:
            user = None
        if user:
            self.object.user = user
            self.object.save()
        else:
            self.object.save()
            serializer = URLSafeSerializer(settings.SECRET_KEY)
            token = serializer.dumps({"representative_id": self.object.pk})
            url = "%s%s" % (
                get_current_domain(self.request),
                reverse('representative-register', kwargs={'token': token})
            )
            send_mail(
                subject=_('Kvietimas prisijungti prie atvirų duomenų portalo'),
                message=_(
                    f'Buvote įtraukti į „{self.dataset}“ duomenų rinkinio '
                    'narių sąrašą, tačiau nesate registruotas Lietuvos '
                    'atvirų duomenų portale. Prašome sekite šia nuoroda, '
                    'kad užsiregistruotumėte ir patvirtintumėte savo '
                    'narystę:\n\n'
                    f'{url}\n\n'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.object.email],
            )
            messages.info(self.request, _(
                "Naudotojui išsiųstas laiškas dėl registracijos"
            ))

        if self.object.has_api_access:
            ApiKey.objects.create(
                api_key=secrets.token_urlsafe(),
                enabled=True,
                representative=self.object
            )

        return HttpResponseRedirect(self.get_success_url())


@login_required
def autocomplete_tags(request, tag_model):
    if isinstance(tag_model, QuerySet):
        queryset = tag_model
        tag_model = queryset.model
    else:
        queryset = tag_model.objects
    options = tag_model.tag_options

    query = request.GET.get("q", "")
    page = int(request.GET.get("p", 1))

    if query:
        if options.force_lowercase:
            query = query.lower()

        if options.autocomplete_view_fulltext:
            lookup = "contains"
        else:
            lookup = "startswith"

        if not options.case_sensitive:
            lookup = f"i{lookup}"

        results = queryset.filter(**{f"name__{lookup}": query})

    else:
        results = queryset.all()

    if options.autocomplete_limit:
        start = options.autocomplete_limit * (page - 1)
        end = options.autocomplete_limit * page
        more = results.count() > end
        results = results.order_by("-count")[start:end]

    response = {"results": [tag.name for tag in results], "more": more}
    return HttpResponse(
        json.dumps(response, cls=DjangoJSONEncoder), content_type="application/json"
    )


class UpdateMemberView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Representative
    form_class = DatasetMemberUpdateForm
    template_name = 'base_form.html'

    def has_permission(self):
        representative = get_object_or_404(
            Representative,
            pk=self.kwargs.get('pk'),
        )
        return has_perm(self.request.user, Action.UPDATE, representative)

    def get_success_url(self):
        return reverse('dataset-members', kwargs={
            'pk': self.kwargs.get('dataset_id'),
        })

    def form_valid(self, form):
        self.object: Representative = form.save()
        if self.object.has_api_access:
            if not self.object.apikey_set.exists():
                ApiKey.objects.create(
                    api_key=secrets.token_urlsafe(),
                    enabled=True,
                    representative=self.object
                )
            elif form.cleaned_data.get('regenerate_api_key'):
                api_key = self.object.apikey_set.first()
                api_key.api_key = secrets.token_urlsafe()
                api_key.enabled = True
                api_key.save()
        else:
            self.object.apikey_set.all().delete()
        return HttpResponseRedirect(self.get_success_url())


class DeleteMemberView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DeleteView,
):
    model = Representative
    template_name = 'confirm_delete.html'

    def has_permission(self):
        representative = get_object_or_404(
            Representative,
            pk=self.kwargs.get('pk'),
        )
        return has_perm(self.request.user, Action.DELETE, representative)

    def get_success_url(self):
        return reverse('dataset-members', kwargs={
            'pk': self.kwargs.get('dataset_id'),
        })


class DatasetProjectsView(DatasetStructureMixin, HistoryMixin, ListView):
    model = Project
    template_name = 'vitrina/datasets/project_list.html'
    context_object_name = 'projects'
    paginate_by = 20

    # HistroyMixin
    object: Dataset
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_projects(self.request.user, self.object, order_value='-created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.object
        context['can_add_projects'] = has_perm(
            self.request.user,
            Action.UPDATE,
            self.object,
        )
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        if self.request.user.is_authenticated:
            context['has_projects'] = (
                get_projects(self.request.user, self.object, check_existence=True, form_query=True)
            )
        else:
            context['has_projects'] = False
        return context


class AddProjectView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView,
):
    model = Dataset
    form_class = AddProjectForm
    template_name = 'base_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_form_kwargs(self):
        kwargs = super(AddProjectView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'dataset': self.dataset})
        return kwargs

    def form_valid(self, form):
        super().form_valid(form)
        self.object = form.save()
        for project in form.cleaned_data['projects']:
            temp_proj = get_object_or_404(Project, pk=project.pk)
            temp_proj.datasets.add(self.object)
        set_comment(Dataset.PROJECT_SET)
        self.object.save()
        return HttpResponseRedirect(
            reverse('dataset-projects', kwargs={'pk': self.object.pk})
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_title'] = self.dataset
        context['parent_url'] = self.dataset.get_absolute_url()
        context['current_title'] = _('Projektų pridėjimas')
        return context


class RemoveProjectView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Dataset
    template_name = 'confirm_remove.html'

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get('pk'))
        self.project = get_object_or_404(Project, pk=self.kwargs.get('project_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.project)

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse('dataset-projects', kwargs={'pk': self.dataset.pk}))

    def delete(self, request, *args, **kwargs):
        self.project.datasets.remove(self.dataset.pk)
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        return reverse('dataset-projects', kwargs={'pk': self.dataset.pk})


class DatasetStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/status.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None)
        statuses = {}
        stat_groups = {}
        if indicator is None:
            indicator = 'dataset-count'
        for d in datasets:
            statuses[d.filter_status] = statuses.get(d.filter_status, 0) + 1
        keys = list(statuses.keys())
        if indicator != 'dataset-count':
            for k in keys:
                id_list = []
                for d in datasets:
                    if d.filter_status == k:
                        id_list.append(d.pk)
                stat_groups[k] = id_list
            for item in stat_groups.keys():
                if indicator == 'download-request-count' or indicator == 'download-object-count':
                    models = Model.objects.filter(dataset_id__in=stat_groups[item]).values_list('metadata__name', flat=True)
                    total = 0
                    if len(models) > 0:
                        for m in models:
                            model_stats = ModelDownloadStats.objects.filter(model=m)
                            if len(model_stats) > 0:
                                for m_st in model_stats:
                                    if indicator == 'download-request-count':
                                        if m_st is not None:
                                            total += m_st.model_requests
                                    elif indicator == 'download-object-count':
                                        if m_st is not None:
                                            total += m_st.model_objects
                    statuses[item] = total
                else:
                    stats = DatasetStats.objects.filter(dataset_id__in=stat_groups[item])
                    if len(stats) > 0:
                        total = 0
                        for st in stats:
                            if indicator == 'request-count':
                                if st.request_count is not None:
                                    total += st.request_count
                                statuses[item] = total
                            elif indicator == 'project-count':
                                if st.project_count is not None:
                                    total += st.project_count
                                statuses[item] = total
                            elif indicator == 'distribution-count':
                                if st.distribution_count is not None:
                                    total += st.distribution_count
                                statuses[item] = total
                            elif indicator == 'object-count':
                                if st.object_count is not None:
                                    total += st.object_count
                                statuses[item] = total
                            elif indicator == 'field-count':
                                if st.field_count is not None:
                                    total += st.field_count
                                statuses[item] = total
                            elif indicator == 'model-count':
                                if st.model_count is not None:
                                    total += st.model_count
                                statuses[item] = total
                            elif indicator == 'level-average':
                                lev = []
                                if st.maturity_level is not None:
                                    lev.append(st.maturity_level)
                                level_avg = int(sum(lev)/len(lev))
                                statuses[item] = level_avg
        values = list(statuses.values())
        for v in values:
            if max_count < int(v):
                max_count = int(v)
        sorted_value_index = np.flip(np.argsort(values))
        sorted_statuses = {keys[i]: values[i] for i in sorted_value_index}

        # data = []
        # status_translations = Comment.get_statuses()
        #
        # inventored_styles = {'borderColor': 'black',
        #                      'backgroundColor': 'rgba(255, 179, 186, 0.9)',
        #                      'fill': True,
        #                      'sort': 1}
        # structured_styles = {'borderColor': 'black',
        #                      'backgroundColor': 'rgba(186,225,255, 0.9)',
        #                      'fill': True,
        #                      'sort': 2}
        # opened_styles = {'borderColor': 'black',
        #                  'backgroundColor': 'rgba(255, 223, 186, 0.9)',
        #                  'fill': True,
        #                  'sort': 3}
        #
        # most_recent_comments = Comment.objects.filter(
        #     content_type=ContentType.objects.get_for_model(Dataset),
        #     object_id__in=datasets.values_list('pk', flat=True),
        #     status__isnull=False).values('object_id')\
        #     .annotate(latest_status_change=Max('created')).values('object_id', 'latest_status_change')\
        #     .order_by('latest_status_change')
        #
        # dataset_status = Comment.objects.filter(
        #     content_type=ContentType.objects.get_for_model(Dataset),
        #     object_id__in=most_recent_comments.values('object_id'),
        #     created__in=most_recent_comments.values('latest_status_change'))\
        #     .annotate(year=ExtractYear('created'), month=ExtractMonth('created'))\
        #     .values('object_id', 'status', 'year', 'month')
        #
        # start_date = most_recent_comments.first().get('latest_status_change') if most_recent_comments else None
        # statuses = dataset_status.order_by('status').values_list('status', flat=True).distinct()
        #
        # if start_date:
        #     labels = pd.period_range(start=start_date,
        #                              end=datetime.date.today(),
        #                              freq='M').tolist()
        #
        #     for item in statuses:
        #         total = 0
        #         temp = []
        #         for label in labels:
        #             total += dataset_status.filter(status=item, year=label.year, month=label.month)\
        #                 .values('object_id')\
        #                 .annotate(count=Count('object_id', distinct=True))\
        #                 .count()
        #             temp.append({'x': _date(label, 'y b'), 'y': total})
        #         dict = {'label': str(status_translations[item]),
        #                 'data': temp,
        #                 'borderWidth': 1}
        #
        #         if item == 'INVENTORED':
        #             dict.update(inventored_styles)
        #         elif item == 'STRUCTURED':
        #             dict.update(structured_styles)
        #         elif item == 'OPENED':
        #             dict.update(opened_styles)
        #
        #         data.append(dict)
        # data = sorted(data, key=lambda x: x['sort'])
        # context['data'] = json.dumps(data)
        # context['graph_title'] = _('Duomenų rinkinių kiekis laike')
        # context['dataset_count'] = len(datasets)
        # context['yAxis_title'] = _('Duomenų rinkiniai')
        # context['xAxis_title'] = _('Laikas')
        # context['stats'] = 'status'
        # context['by_indicator'] = stat_groups
        context['status_data'] = sorted_statuses
        context['max_count'] = max_count
        context['active_filter'] = 'status'
        context['active_indicator'] = indicator
        return context


class DatasetManagementsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/jurisdictions.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        all_orgs = context['jurisdiction_facet']
        indicator = self.request.GET.get('indicator', None)
        modified_jurisdictions = []
        if indicator is None:
            indicator = 'dataset-count'
        for org in all_orgs:
            id_list = []
            current = Organization.objects.get(title=org.get('display_value'))
            org_datasets = Dataset.objects.filter(organization=current).values_list('id', flat=True)
            if len(org_datasets) > 0:
                for d in org_datasets:
                    id_list.append(d)
                org['dataset_ids'] = id_list
            children = current.get_children()
            child_titles = []
            if len(children) > 0:
                exists = 0
                for ch in children:
                    child_titles.append(ch.title)
                for single in all_orgs:
                    if single['display_value'] in child_titles:
                        exists += 1
                if exists == 0:
                    org['has_orgs'] = False
            else:
                org['has_orgs'] = False
            if indicator == 'dataset-count':
                if max_count < org.get('count'):
                    max_count = org.get('count')
            modified_jurisdictions.append(org)
            print(modified_jurisdictions)
        if indicator != 'dataset-count':
            for single in modified_jurisdictions:
                if 'dataset_ids' in single:
                    if indicator == 'download-request-count' or indicator == 'download-object-count':
                        models = Model.objects.filter(dataset_id__in=single['dataset_ids']).values_list('metadata__name', flat=True)
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == 'download-request-count':
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == 'download-object-count':
                                            if m_st is not None:
                                                total += m_st.model_objects
                        single['stats'] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=single['dataset_ids'])
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                if indicator == 'request-count':
                                    if st.request_count is not None:
                                        total += st.request_count
                                    single['stats'] = total
                                elif indicator == 'project-count':
                                    if st.project_count is not None:
                                        total += st.project_count
                                    single['stats'] = total
                                elif indicator == 'distribution-count':
                                    if st.distribution_count is not None:
                                        total += st.distribution_count
                                    single['stats'] = total
                                elif indicator == 'object-count':
                                    if st.object_count is not None:
                                        total += st.object_count
                                    single['stats'] = total
                                elif indicator == 'field-count':
                                    if st.field_count is not None:
                                        total += st.field_count
                                    single['stats'] = total
                                elif indicator == 'model-count':
                                    if st.model_count is not None:
                                        total += st.model_count
                                    single['stats'] = total
                                elif indicator == 'level-average':
                                    lev = []
                                    if st.maturity_level is not None:
                                        lev.append(st.maturity_level)
                                    level_avg = int(sum(lev) / len(lev))
                                    single['stats'] = level_avg
                        else:
                            single['stats'] = 0
                    if max_count < single.get('stats'):
                        max_count = single.get('stats')
                else:
                    single['stats'] = 0
            modified_jurisdictions = sorted(modified_jurisdictions, key=lambda dd: dd['stats'], reverse=True)
        context['jurisdiction_data'] = modified_jurisdictions
        context['max_count'] = max_count
        context['active_filter'] = 'jurisdiction'
        context['active_indicator'] = indicator
        return context


class DatasetsLevelView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/level.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None)
        levels = {}
        stat_groups = {}
        if indicator is None:
            indicator = 'dataset-count'
        for d in datasets:
            lev = d.level
            levels[lev] = levels.get(lev, 0) + 1
        keys = list(levels.keys())
        if indicator != 'dataset-count':
            for le in levels.keys():
                id_list = []
                for d in datasets:
                    if d.level is not None:
                        if d.level == le:
                            id_list.append(d.pk)
                stat_groups[le] = id_list
            for item in stat_groups.keys():
                if indicator == 'download-request-count' or indicator == 'download-object-count':
                    models = Model.objects.filter(dataset_id__in=stat_groups[item]).values_list('metadata__name', flat=True)
                    total = 0
                    if len(models) > 0:
                        for m in models:
                            model_stats = ModelDownloadStats.objects.filter(model=m)
                            if len(model_stats) > 0:
                                for m_st in model_stats:
                                    if indicator == 'download-request-count':
                                        if m_st is not None:
                                            total += m_st.model_requests
                                    elif indicator == 'download-object-count':
                                        if m_st is not None:
                                            total += m_st.model_objects
                    levels[item] = total
                else:
                    stats = DatasetStats.objects.filter(maturity_level__in=stat_groups[item])
                    if len(stats) > 0:
                        total = 0
                        for st in stats:
                            if indicator == 'request-count':
                                if st.request_count is not None:
                                    total += st.request_count
                                levels[item] = total
                            elif indicator == 'project-count':
                                if st.project_count is not None:
                                    total += st.project_count
                                levels[item] = total
                            elif indicator == 'distribution-count':
                                if st.distribution_count is not None:
                                    total += st.distribution_count
                                levels[item] = total
                            elif indicator == 'object-count':
                                if st.object_count is not None:
                                    total += st.object_count
                                levels[item] = total
                            elif indicator == 'field-count':
                                if st.field_count is not None:
                                    total += st.field_count
                                levels[item] = total
                            elif indicator == 'model-count':
                                if st.model_count is not None:
                                    total += st.model_count
                                levels[item] = total
                            elif indicator == 'level-average':
                                lev = []
                                if st.maturity_level is not None:
                                    lev.append(st.maturity_level)
                                level_avg = int(sum(lev) / len(lev))
                                levels[item] = level_avg
                    else:
                        levels[item] = 0
        values = list(levels.values())
        for v in values:
            if max_count < v:
                max_count = v
        sorted_value_index = np.flip(np.argsort(values))
        sorted_levels = {keys[i]: values[i] for i in sorted_value_index}
        context['level_data'] = sorted_levels
        context['max_count'] = max_count
        context['active_filter'] = 'level'
        context['active_indicator'] = indicator
        return context


class DatasetsOrganizationsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/organizations.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None)
        orgs = {}
        stat_groups = {}
        if indicator is None:
            indicator = 'dataset-count'
        for d in datasets:
            current = Organization.objects.get(id=d.organization[0])
            orgs[current] = orgs.get(current, 0) + 1
        keys = list(orgs.keys())
        if indicator != 'dataset-count':
            for k in keys:
                id_list = []
                for d in datasets:
                    if d.organization[0] == k.pk:
                        id_list.append(d.pk)
                stat_groups[k] = id_list
            for item in stat_groups.keys():
                if indicator == 'download-request-count' or indicator == 'download-object-count':
                    models = Model.objects.filter(dataset_id__in=stat_groups[item]).values_list('metadata__name', flat=True)
                    total = 0
                    if len(models) > 0:
                        for m in models:
                            model_stats = ModelDownloadStats.objects.filter(model=m)
                            if len(model_stats) > 0:
                                for m_st in model_stats:
                                    if indicator == 'download-request-count':
                                        if m_st is not None:
                                            total += m_st.model_requests
                                    elif indicator == 'download-object-count':
                                        if m_st is not None:
                                            total += m_st.model_objects
                    orgs[item] = total
                else:
                    stats = DatasetStats.objects.filter(dataset_id__in=stat_groups[item])
                    if len(stats) > 0:
                        total = 0
                        for st in stats:
                            if indicator == 'request-count':
                                if st.request_count is not None:
                                    total += st.request_count
                                orgs[item] = total
                            elif indicator == 'project-count':
                                if st.project_count is not None:
                                    total += st.project_count
                                orgs[item] = total
                            elif indicator == 'distribution-count':
                                if st.distribution_count is not None:
                                    total += st.distribution_count
                                orgs[item] = total
                            elif indicator == 'object-count':
                                if st.object_count is not None:
                                    total += st.object_count
                                orgs[item] = total
                            elif indicator == 'field-count':
                                if st.field_count is not None:
                                    total += st.field_count
                                orgs[item] = total
                            elif indicator == 'model-count':
                                if st.model_count is not None:
                                    total += st.model_count
                                orgs[item] = total
                            elif indicator == 'level-average':
                                lev = []
                                if st.maturity_level is not None:
                                    lev.append(st.maturity_level)
                                level_avg = int(sum(lev) / len(lev))
                                orgs[item] = level_avg
                    else:
                        orgs[item] = 0
        values = list(orgs.values())
        for v in values:
            if max_count < v:
                max_count = v
        sorted_value_index = np.flip(np.argsort(values))
        sorted_orgs = {keys[i]: values[i] for i in sorted_value_index}
        context['organization_data'] = sorted_orgs
        context['max_count'] = max_count
        context['active_filter'] = 'organizations'
        context['active_indicator'] = indicator
        return context

class OrganizationStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/organizations.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        indicator = self.request.GET.get('indicator', None)
        orgs = {}
        keys = list(orgs.keys())
        values = list(orgs.values())
        for v in values:
            if max_count < v:
                max_count = v
        sorted_value_index = np.flip(np.argsort(values))
        sorted_orgs = {keys[i]: values[i] for i in sorted_value_index}
        context['organization_data'] = sorted_orgs
        context['max_count'] = max_count
        context['active_filter'] = 'organizations'
        context['active_indicator'] = indicator
        return context

class DatasetsTagsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/tag.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None)
        tags = {}
        stat_groups = {}
        if indicator is None:
            indicator = 'dataset-count'
        for d in datasets:
            if d.tags is not None:
                for t in d.tags:
                    tags[t.strip().capitalize()] = tags.get(t.strip().capitalize(), 0) + 1
        keys = list(tags.keys())
        if indicator != 'dataset-count':
            for k in keys:
                id_list = []
                for d in datasets:
                    if d.tags is not None:
                        for tag in d.tags:
                            if tag == k:
                                id_list.append(d.pk)
                stat_groups[k] = id_list
            for item in stat_groups.keys():
                stats = DatasetStats.objects.filter(dataset_id__in=stat_groups[item])
                if len(stats) > 0:
                    total = 0
                    for st in stats:
                        if indicator == 'request-count':
                            if st.request_count is not None:
                                total += st.request_count
                            tags[item] = total
                        elif indicator == 'project-count':
                            if st.project_count is not None:
                                total += st.project_count
                            tags[item] = total
                        elif indicator == 'distribution-count':
                            if st.distribution_count is not None:
                                total += st.distribution_count
                            tags[item] = total
                        elif indicator == 'object-count':
                            if st.object_count is not None:
                                total += st.object_count
                            tags[item] = total
                        elif indicator == 'field-count':
                            if st.field_count is not None:
                                total += st.field_count
                            tags[item] = total
                        elif indicator == 'model-count':
                            if st.model_count is not None:
                                total += st.model_count
                            tags[item] = total
                        elif indicator == 'level-average':
                            lev = []
                            if st.maturity_level is not None:
                                lev.append(st.maturity_level)
                            level_avg = int(sum(lev) / len(lev))
                            tags[item] = level_avg
                else:
                    tags[item] = 0
        values = list(tags.values())
        for v in values:
            if max_count < v:
                max_count = v
        sorted_value_index = np.flip(np.argsort(values))
        sorted_tags = {keys[i]: values[i] for i in sorted_value_index}
        if len(keys) > 100:
            context['trimmed'] = True
            sorted_tags = dict(itertools.islice(sorted_tags.items(), 100))
        context['tag_data'] = sorted_tags
        context['max_count'] = max_count
        context['active_filter'] = 'tag'
        context['active_indicator'] = indicator
        return context

class DatasetsFormatView(DatasetListView):
        facet_fields = DatasetListView.facet_fields
        template_name = 'vitrina/datasets/formats.html'
        paginate_by = 0

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            max_count = 0
            datasets = self.get_queryset()
            indicator = self.request.GET.get('indicator', None)
            formats = {}
            stat_groups = {}
            if indicator is None:
                indicator = 'dataset-count'
            for d in datasets:
                if d.formats is not None:
                    for f in d.formats:
                        formats[f.strip().title()] = formats.get(f.strip().title(), 0) + 1
            keys = list(formats.keys())
            if indicator != 'dataset-count':
                for k in keys:
                    id_list = []
                    for d in datasets:
                        if d.formats is not None:
                            for format in d.formats:
                                if format.strip().title() == k:
                                    id_list.append(d.pk)
                    stat_groups[k] = id_list
                for item in stat_groups.keys():
                    if indicator == 'download-request-count' or indicator == 'download-object-count':
                        models = Model.objects.filter(dataset_id__in=stat_groups[item]).values_list('metadata__name', flat=True)
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == 'download-request-count':
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == 'download-object-count':
                                            if m_st is not None:
                                                total += m_st.model_objects
                        formats[item] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=stat_groups[item])
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                if indicator == 'request-count':
                                    if st.request_count is not None:
                                        total += st.request_count
                                    formats[item] = total
                                elif indicator == 'project-count':
                                    if st.project_count is not None:
                                        total += st.project_count
                                    formats[item] = total
                                elif indicator == 'distribution-count':
                                    if st.distribution_count is not None:
                                        total += st.distribution_count
                                    formats[item] = total
                                elif indicator == 'object-count':
                                    if st.object_count is not None:
                                        total += st.object_count
                                    formats[item] = total
                                elif indicator == 'field-count':
                                    if st.field_count is not None:
                                        total += st.field_count
                                    formats[item] = total
                                elif indicator == 'model-count':
                                    if st.model_count is not None:
                                        total += st.model_count
                                    formats[item] = total
                                elif indicator == 'level-average':
                                    lev = []
                                    if st.maturity_level is not None:
                                        lev.append(st.maturity_level)
                                    level_avg = int(sum(lev) / len(lev))
                                    formats[item] = level_avg
                        else:
                            formats[item] = 0
            values = list(formats.values())
            for v in values:
                if max_count < v:
                    max_count = v
            sorted_value_index = np.flip(np.argsort(values))
            sorted_formats = {keys[i]: values[i] for i in sorted_value_index}
            context['format_data'] = sorted_formats
            context['max_count'] = max_count
            context['active_filter'] = 'format'
            context['active_indicator'] = indicator
            return context

class DatasetsFrequencyView(DatasetListView):
        facet_fields = DatasetListView.facet_fields
        template_name = 'vitrina/datasets/frequency.html'
        paginate_by = 0

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            max_count = 0
            datasets = self.get_queryset()
            indicator = self.request.GET.get('indicator', None)
            frequencies = {}
            stat_groups = {}
            if indicator is None:
                indicator = 'dataset-count'
            for d in datasets:
                if d.frequency is not None:
                    freq = Frequency.objects.get(id=d.frequency)
                    frequencies[freq] = frequencies.get(freq, 0) + 1
            keys = list(frequencies.keys())
            if indicator != 'dataset-count':
                for k in keys:
                    id_list = []
                    for d in datasets:
                        if d.frequency is not None:
                            freq = Frequency.objects.get(id=d.frequency)
                            if freq == k:
                                id_list.append(d.pk)
                    stat_groups[k] = id_list
                for item in stat_groups.keys():
                    if indicator == 'download-request-count' or indicator == 'download-object-count':
                        models = Model.objects.filter(dataset_id__in=stat_groups[item]).values_list('metadata__name', flat=True)
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == 'download-request-count':
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == 'download-object-count':
                                            if m_st is not None:
                                                total += m_st.model_objects
                        frequencies[item] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=stat_groups[item])
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                if indicator == 'request-count':
                                    if st.request_count is not None:
                                        total += st.request_count
                                    frequencies[item] = total
                                elif indicator == 'project-count':
                                    if st.project_count is not None:
                                        total += st.project_count
                                    frequencies[item] = total
                                elif indicator == 'distribution-count':
                                    if st.distribution_count is not None:
                                        total += st.distribution_count
                                    frequencies[item] = total
                                elif indicator == 'object-count':
                                    if st.object_count is not None:
                                        total += st.object_count
                                    frequencies[item] = total
                                elif indicator == 'field-count':
                                    if st.field_count is not None:
                                        total += st.field_count
                                    frequencies[item] = total
                                elif indicator == 'model-count':
                                    if st.model_count is not None:
                                        total += st.model_count
                                    frequencies[item] = total
                                elif indicator == 'level-average':
                                    lev = []
                                    if st.maturity_level is not None:
                                        lev.append(st.maturity_level)
                                    level_avg = int(sum(lev) / len(lev))
                                    frequencies[item] = level_avg
                        else:
                            frequencies[item] = 0
            values = list(frequencies.values())
            for v in values:
                if max_count < v:
                    max_count = v
            sorted_value_index = np.flip(np.argsort(values))
            sorted_frequencies = {keys[i]: values[i] for i in sorted_value_index}
            context['frequency_data'] = sorted_frequencies
            context['max_count'] = max_count
            context['active_filter'] = 'frequency'
            context['active_indicator'] = indicator
            return context

class JurisdictionStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/jurisdictions.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        current_org = Organization.objects.get(id=self.kwargs.get('pk'))
        child_orgs = current_org.get_children()
        indicator = self.request.GET.get('indicator', None)
        filtered_orgs = []
        if indicator is None:
            indicator = 'dataset-count'
        for org in child_orgs:
            modified = {}
            id_list = []
            datasets = Dataset.objects.filter(organization=org).values_list('id', flat=True)
            if len(datasets) > 0:
                for d in datasets:
                    id_list.append(d)
            modified[org] = id_list
            filtered_orgs.append(modified)
        result = []
        for single in filtered_orgs:
            single_dict = {}
            for k, v in single.items():
                single_dict['id'] = k.pk
                single_dict['title'] = k.title
                single_dict['url'] = '?selected_facets=jurisdiction_exact:' + str(k.pk)
                if len(k.get_children()) > 0:
                    single_dict['has_orgs'] = True
                else:
                    single_dict['has_orgs'] = False
                if indicator == 'dataset-count':
                    single_dict['count'] = len(v)
                    if max_count < len(v):
                        max_count = len(v)
                elif indicator != 'dataset-count':
                    if indicator == 'download-request-count' or indicator == 'download-object-count':
                        models = Model.objects.filter(dataset_id__in=v).values_list('metadata__name', flat=True)
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == 'download-request-count':
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == 'download-object-count':
                                            if m_st is not None:
                                                total += m_st.model_objects
                        single_dict['count'] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=v)
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                if indicator == 'request-count':
                                    if st.request_count is not None:
                                        total += st.request_count
                                    single_dict['count'] = total
                                elif indicator == 'project-count':
                                    if st.project_count is not None:
                                        total += st.project_count
                                    single_dict['count'] = total
                                elif indicator == 'distribution-count':
                                    if st.distribution_count is not None:
                                        total += st.distribution_count
                                    single_dict['count'] = total
                                elif indicator == 'object-count':
                                    if st.object_count is not None:
                                        total += st.object_count
                                    single_dict['count'] = total
                                elif indicator == 'field-count':
                                    if st.field_count is not None:
                                        total += st.field_count
                                    single_dict['count'] = total
                                elif indicator == 'model-count':
                                    if st.model_count is not None:
                                        total += st.model_count
                                    single_dict['count'] = total
                                elif indicator == 'level-average':
                                    lev = []
                                    if st.maturity_level is not None:
                                        lev.append(st.maturity_level)
                                    level_avg = int(sum(lev) / len(lev))
                                    single_dict['count'] = level_avg
                            if max_count < single_dict.get('count'):
                                max_count = single_dict.get('count')
                        else:
                            single_dict['count'] = 0
            result.append(single_dict)
            result = sorted(result, key=lambda dd: dd['count'], reverse=True)
        context['single_org'] = True
        context['jurisdiction_data'] = result
        context['max_count'] = max_count
        context['current_object'] = self.kwargs.get('pk')
        context['active_filter'] = 'jurisdiction'
        context['active_indicator'] = indicator
        return context

class DatasetsStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/categories.html'
    paginate_by = 0

    # def get_date_labels(self):
    #     oldest_dataset_date = Dataset.objects.order_by('created').first().created
    #     return period_range(start=oldest_dataset_date, end=now(), freq='Y').astype(str).tolist()
    #
    # def get_categories(self):
    #     return [
    #         {'title': cat.title, 'id': cat.id} for cat in Category.objects.filter(featured=True).order_by('title')
    #     ]
    #
    # def get_color(self, year):
    #     color_map = {
    #         '2019': '#03256C',
    #         '2020': '#2541B2',
    #         '2021': '#1768AC',
    #         "2022": '#06BEE1',
    #         "2023": "#4193A2",
    #         # FIXME: this should net be hardcoded, use colormaps:
    #         #        https://matplotlib.org/stable/tutorials/colors/colormaps.html
    #         #        (maybe `winter`?)
    #     }
    #     return color_map.get(year)
    #
    # def get_statistics_data(self):
    #     categories = self.get_categories()
    #     query_set = self.get_queryset()
    #     data = {
    #         'labels': [cat.get('title') for cat in categories]
    #     }
    #     datasets = []
    #     date_labels = self.get_date_labels()
    #     for date_label in date_labels:
    #         dataset_counts = []
    #         for category in categories:
    #             filtered_ids = query_set.filter(category__id=category.get('id')).values_list('pk', flat=True)
    #             created_date = datetime.datetime(int(date_label), 1, 1)
    #             created_date = make_aware(created_date)
    #             dataset_counts.append(
    #                 Dataset.objects.filter(id__in=filtered_ids, created__lt=created_date).count()
    #             )
    #         datasets.append(
    #             {
    #                 'label': date_label,
    #                 'data': dataset_counts,
    #                 'backgroundColor': self.get_color(date_label)
    #
    #             }
    #         )
    #     data['datasets'] = datasets
    #     return data, query_set

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     max_count = 0
    #     data, qs = self.get_statistics_data()
    #     context['data'] = data
    #     context['dataset_count'] = len(qs)
    #     context['graph_title'] = 'Duomenų rinkinių atvėrimo progresas'
    #     return context
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        parent_cats = context['parent_category_facet']
        all_cats = context['category_facet']
        modified_cats = []
        for cat in parent_cats:
            current_category = Category.objects.get(title=cat.get('display_value'))
            children = Category.get_children(current_category)
            child_titles = []
            if len(children) > 0:
                existing_count = 0
                for child in children:
                    child_titles.append(child.title)
                for single in all_cats:
                    if single['display_value'] in child_titles:
                        existing_count += 1
                if existing_count == 0:
                    cat['has_cats'] = False
            else:
                cat['has_cats'] = False
            if max_count < cat.get('count'):
                max_count = cat.get('count')
            modified_cats.append(cat)
        context['categories'] = modified_cats
        context['max_count'] = max_count
        context['active_filter'] = 'categories'
        return context


class DatasetsCategoriesView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/categories.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        parent_cats = context['parent_category_facet']
        all_cats = context['category_facet']
        indicator = self.request.GET.get('indicator', None)
        modified_cats = []
        if indicator is None:
            indicator = 'dataset-count'
        for cat in parent_cats:
            id_list = []
            current_category = Category.objects.get(title=cat.get('display_value'))
            category_datasets = Dataset.objects.filter(category=current_category)
            if len(category_datasets) > 0:
                for d in category_datasets:
                    id_list.append(d.pk)
                cat['dataset_ids'] = id_list
            children = Category.get_children(current_category)
            child_titles = []
            if len(children) > 0:
                existing_count = 0
                for child in children:
                    child_titles.append(child.title)
                for single in all_cats:
                    if single['display_value'] in child_titles:
                        existing_count += 1
                if existing_count == 0:
                    cat['has_cats'] = False
            else:
                cat['has_cats'] = False
            if indicator == 'dataset-count':
                if max_count < cat.get('count'):
                    max_count = cat.get('count')
            modified_cats.append(cat)
        if indicator != 'dataset-count':
            for single in modified_cats:
                if 'dataset_ids' in single:
                    if indicator == 'download-request-count' or indicator == 'download-object-count':
                        models = Model.objects.filter(dataset_id__in=single['dataset_ids']).values_list('metadata__name', flat=True)
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == 'download-request-count':
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == 'download-object-count':
                                            if m_st is not None:
                                                total += m_st.model_objects
                        single['stats'] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=single['dataset_ids'])
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                if indicator == 'request-count':
                                    if st.request_count is not None:
                                        total += st.request_count
                                    single['stats'] = total
                                elif indicator == 'project-count':
                                    if st.project_count is not None:
                                        total += st.project_count
                                    single['stats'] = total
                                elif indicator == 'distribution-count':
                                    if st.distribution_count is not None:
                                        total += st.distribution_count
                                    single['stats'] = total
                                elif indicator == 'object-count':
                                    if st.object_count is not None:
                                        total += st.object_count
                                    single['stats'] = total
                                elif indicator == 'field-count':
                                    if st.field_count is not None:
                                        total += st.field_count
                                    single['stats'] = total
                                elif indicator == 'model-count':
                                    if st.model_count is not None:
                                        total += st.model_count
                                    single['stats'] = total
                                elif indicator == 'level-average':
                                    lev = []
                                    if st.maturity_level is not None:
                                        lev.append(st.maturity_level)
                                    level_avg = int(sum(lev) / len(lev))
                                    single['stats'] = level_avg
                                if max_count < single.get('stats'):
                                    max_count = single.get('stats')
                        else:
                            single['stats'] = 0
                else:
                    single['stats'] = 0
            modified_cats = sorted(modified_cats, key=lambda dd: dd['stats'], reverse=True)
        context['categories'] = modified_cats
        context['max_count'] = max_count
        context['active_filter'] = 'category'
        context['active_indicator'] = indicator
        return context

class CategoryStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/categories.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        all_cats = context['category_facet']
        child_titles = []
        cat_titles = []
        indicator = self.request.GET.get('indicator', None)
        if indicator is None:
            indicator = 'dataset-count'
        for cat in all_cats:
            cat_titles.append(cat['display_value'])
        filtered_cats = []
        parent_category = Category.objects.get(id=self.kwargs.get('pk'))
        children = Category.get_children(parent_category)
        for child in children:
            child_titles.append(child.title)
        for single_cat in all_cats:
            if single_cat['display_value'] in child_titles:
                cat_object = Category.objects.get(title=single_cat['display_value'])
                subcategories = Category.get_children(cat_object)
                if len(subcategories) > 0:
                    exists = 0
                    for ss in subcategories:
                        if ss.title in cat_titles:
                            exists += 1
                    if exists == 0:
                        single_cat['has_cats'] = False
                else:
                    single_cat['has_cats'] = False
                if max_count < single_cat.get('count'):
                    max_count = single_cat.get('count')
                filtered_cats.append(single_cat)
        if indicator != 'dataset-count':
            for k in filtered_cats:
                id_list = []
                c_cat = Category.objects.get(title=k.get('display_value'))
                cat_datasets = Dataset.objects.filter(category=c_cat.pk)
                if len(cat_datasets) > 0:
                    for dd in cat_datasets:
                        id_list.append(dd.pk)
                    if indicator == 'download-request-count' or indicator == 'download-object-count':
                        models = Model.objects.filter(dataset_id__in=id_list).values_list('metadata__name', flat=True)
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == 'download-request-count':
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == 'download-object-count':
                                            if m_st is not None:
                                                total += m_st.model_objects
                        k['stats'] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=id_list)
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                if indicator == 'request-count':
                                    if st.request_count is not None:
                                        total += st.request_count
                                    k['stats'] = total
                                elif indicator == 'project-count':
                                    if st.project_count is not None:
                                        total += st.project_count
                                    k['stats'] = total
                                elif indicator == 'distribution-count':
                                    if st.distribution_count is not None:
                                        total += st.distribution_count
                                    k['stats'] = total
                                elif indicator == 'object-count':
                                    if st.object_count is not None:
                                        total += st.object_count
                                    k['stats'] = total
                                elif indicator == 'field-count':
                                    if st.field_count is not None:
                                        total += st.field_count
                                    k['stats'] = total
                                elif indicator == 'model-count':
                                    if st.model_count is not None:
                                        total += st.model_count
                                    k['stats'] = total
                                elif indicator == 'level-average':
                                    lev = []
                                    if st.maturity_level is not None:
                                        lev.append(st.maturity_level)
                                    level_avg = int(sum(lev) / len(lev))
                                    k['stats'] = level_avg
                                if max_count < k.get('stats'):
                                    max_count = k.get('stats')
                        else:
                            k['stats'] = 0
            filtered_cats = sorted(filtered_cats, key=lambda d: d['stats'], reverse=True)
        context['max_count'] = max_count
        context['categories'] = filtered_cats
        context['current_object'] = self.kwargs.get('pk')
        context['active_filter'] = 'category'
        context['active_indicator'] = indicator
        return context


class PublicationStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None)
        year_stats = {}
        # quarter_stats = {}
        # monthly_stats = {}
        if indicator is None:
            indicator = 'dataset-count'
        for dataset in datasets:
            published = dataset.published
            if published is not None:
                year_published = published.year
                year_stats[year_published] = year_stats.get(year_published, 0) + 1
                # quarter = str(year_published) + "-Q" + str(pd.Timestamp(published).quarter)
                # quarter_stats[quarter] = quarter_stats.get(quarter, 0) + 1
                # month = str(year_published) + "-" + str('%02d' % published.month)
                # monthly_stats[month] = monthly_stats.get(month, 0) + 1
        if indicator != 'dataset-count':
            for yr in year_stats.keys():
                start_date = datetime.strptime(str(yr) + "-1-1", '%Y-%m-%d')
                end_date = datetime.strptime(str(yr) + "-12-31", '%Y-%m-%d')
                tz = pytz.timezone('Europe/Vilnius')
                filtered_datasets = datasets.filter(published__range=[tz.localize(start_date), tz.localize(end_date)])
                dataset_ids = []
                for fd in filtered_datasets:
                    dataset_ids.append(fd.pk)
                if indicator == 'download-request-count' or indicator == 'download-object-count':
                    models = Model.objects.filter(dataset_id__in=dataset_ids).values_list('metadata__name', flat=True)
                    total = 0
                    if len(models) > 0:
                        for m in models:
                            model_stats = ModelDownloadStats.objects.filter(model=m)
                            if len(model_stats) > 0:
                                for m_st in model_stats:
                                    if indicator == 'download-request-count':
                                        if m_st is not None:
                                            total += m_st.model_requests
                                    elif indicator == 'download-object-count':
                                        if m_st is not None:
                                            total += m_st.model_objects
                    year_stats[yr] = total
                else:
                    stats = DatasetStats.objects.filter(dataset_id__in=dataset_ids)
                    if len(stats) > 0:
                        total = 0
                        for st in stats:
                            if indicator == 'request-count':
                                if st.request_count is not None:
                                    total += st.request_count
                                year_stats[yr] = total
                            elif indicator == 'project-count':
                                if st.project_count is not None:
                                    total += st.project_count
                                year_stats[yr] = total
                            elif indicator == 'distribution-count':
                                if st.distribution_count is not None:
                                    total += st.distribution_count
                                year_stats[yr] = total
                            elif indicator == 'object-count':
                                if st.object_count is not None:
                                    total += st.object_count
                                year_stats[yr] = total
                            elif indicator == 'field-count':
                                if st.field_count is not None:
                                    total += st.field_count
                                year_stats[yr] = total
                            elif indicator == 'model-count':
                                if st.model_count is not None:
                                    total += st.model_count
                                year_stats[yr] = total
                            elif indicator == 'level-average':
                                lev = []
                                if st.maturity_level is not None:
                                    lev.append(st.maturity_level)
                                level_avg = int(sum(lev)/len(lev))
                                year_stats[yr] = level_avg
                    else:
                        year_stats[yr] = 0

        for key, value in year_stats.items():
            if max_count < value:
                max_count = value

        context['year_stats'] = year_stats
        context['max_count'] = max_count
        context['active_filter'] = 'publication'
        context['active_indicator'] = indicator
        return context

class YearStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None)
        year_stats = {}
        quarter_stats = {}
        selected_year = str(self.kwargs['year'])
        if indicator is None:
            indicator = 'dataset-count'
        for dataset in datasets:
            published = dataset.published
            if published is not None:
                year_published = published.year
                year_stats[year_published] = year_stats.get(year_published, 0) + 1
                quarter = str(year_published) + "-Q" + str(pd.Timestamp(published).quarter)
                quarter_stats[quarter] = quarter_stats.get(quarter, 0) + 1
        if indicator != 'dataset-count':
            for k in quarter_stats.keys():
                tz = pytz.timezone('Europe/Vilnius')
                if selected_year in k:
                    if '-Q1' in k:
                        start = datetime.strptime(str(selected_year) + "-1-1", '%Y-%m-%d')
                        end = datetime.strptime(str(selected_year) + "-3-31", '%Y-%m-%d')
                    elif '-Q2' in k:
                        start = datetime.strptime(str(selected_year) + "-4-1", '%Y-%m-%d')
                        end = datetime.strptime(str(selected_year) + "-6-30", '%Y-%m-%d')
                    elif '-Q3' in k:
                        start = datetime.strptime(str(selected_year) + "-7-1", '%Y-%m-%d')
                        end = datetime.strptime(str(selected_year) + "-9-30", '%Y-%m-%d')
                    else:
                        start = datetime.strptime(str(selected_year) + "-10-1", '%Y-%m-%d')
                        end = datetime.strptime(str(selected_year) + "-12-31", '%Y-%m-%d')
                    filtered_datasets = datasets.filter(published__range=[tz.localize(start), tz.localize(end)])
                    dataset_ids = []
                    for fd in filtered_datasets:
                        dataset_ids.append(fd.pk)
                    if indicator == 'download-request-count' or indicator == 'download-object-count':
                        models = Model.objects.filter(dataset_id__in=dataset_ids).values_list('metadata__name', flat=True)
                        total = 0
                        if len(models) > 0:
                            for m in models:
                                model_stats = ModelDownloadStats.objects.filter(model=m)
                                if len(model_stats) > 0:
                                    for m_st in model_stats:
                                        if indicator == 'download-request-count':
                                            if m_st is not None:
                                                total += m_st.model_requests
                                        elif indicator == 'download-object-count':
                                            if m_st is not None:
                                                total += m_st.model_objects
                        quarter_stats[k] = total
                    else:
                        stats = DatasetStats.objects.filter(dataset_id__in=dataset_ids)
                        if len(stats) > 0:
                            total = 0
                            for st in stats:
                                if indicator == 'request-count':
                                    if st.request_count is not None:
                                        total += st.request_count
                                    quarter_stats[k] = total
                                elif indicator == 'project-count':
                                    if st.project_count is not None:
                                        total += st.project_count
                                    quarter_stats[k] = total
                                elif indicator == 'distribution-count':
                                    if st.distribution_count is not None:
                                        total += st.distribution_count
                                    quarter_stats[k] = total
                                elif indicator == 'object-count':
                                    if st.object_count is not None:
                                        total += st.object_count
                                    quarter_stats[k] = total
                                elif indicator == 'field-count':
                                    if st.field_count is not None:
                                        total += st.field_count
                                    quarter_stats[k] = total
                                elif indicator == 'model-count':
                                    if st.model_count is not None:
                                        total += st.model_count
                                    quarter_stats[k] = total
                                elif indicator == 'level-average':
                                    lev = []
                                    if st.maturity_level is not None:
                                        lev.append(st.maturity_level)
                                    level_avg = int(sum(lev) / len(lev))
                                    quarter_stats[k] = level_avg
                        else:
                            quarter_stats[k] = 0
        for key, value in quarter_stats.items():
            if max_count < value:
                max_count = value
        context['selected_year'] = selected_year
        context['year_stats'] = quarter_stats
        context['max_count'] = max_count
        context['current_object'] = str('year/' + selected_year)
        context['active_filter'] = 'publication'
        context['active_indicator'] = indicator
        return context


class QuarterStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None)
        # year_stats = {}
        # quarter_stats = {}
        monthly_stats = {}
        selected_quarter = str(self.kwargs['quarter'])
        if indicator is None:
            indicator = 'dataset-count'
        for dataset in datasets:
            published = dataset.published
            if published is not None:
                year_published = published.year
                if str(year_published) in selected_quarter:
                    quarter = str(year_published) + "-Q" + str(pd.Timestamp(published).quarter)
                    if quarter == selected_quarter:
                        month = str(year_published) + "-" + str('%02d' % published.month)
                        monthly_stats[month] = monthly_stats.get(month, 0) + 1
        if indicator != 'dataset-count':
            for k in monthly_stats.keys():
                tz = pytz.timezone('Europe/Vilnius')
                start = datetime.strptime(str(k) + "-1", '%Y-%m-%d')
                end = datetime.strptime(str(k) + "-28", '%Y-%m-%d')
                filtered_datasets = datasets.filter(published__range=[tz.localize(start), tz.localize(end)])
                dataset_ids = []
                for fd in filtered_datasets:
                    dataset_ids.append(fd.pk)
                if indicator == 'download-request-count' or indicator == 'download-object-count':
                    models = Model.objects.filter(dataset_id__in=dataset_ids).values_list('metadata__name', flat=True)
                    total = 0
                    if len(models) > 0:
                        for m in models:
                            model_stats = ModelDownloadStats.objects.filter(model=m)
                            if len(model_stats) > 0:
                                for m_st in model_stats:
                                    if indicator == 'download-request-count':
                                        if m_st is not None:
                                            total += m_st.model_requests
                                    elif indicator == 'download-object-count':
                                        if m_st is not None:
                                            total += m_st.model_objects
                    monthly_stats[k] = total
                else:
                    stats = DatasetStats.objects.filter(dataset_id__in=dataset_ids)
                    if len(stats) > 0:
                        total = 0
                        for st in stats:
                            if indicator == 'request-count':
                                if st.request_count is not None:
                                    total += st.request_count
                                monthly_stats[k] = total
                            elif indicator == 'project-count':
                                if st.project_count is not None:
                                    total += st.project_count
                                monthly_stats[k] = total
                            elif indicator == 'distribution-count':
                                if st.distribution_count is not None:
                                    total += st.distribution_count
                                monthly_stats[k] = total
                            elif indicator == 'object-count':
                                if st.object_count is not None:
                                    total += st.object_count
                                monthly_stats[k] = total
                            elif indicator == 'field-count':
                                if st.field_count is not None:
                                    total += st.field_count
                                monthly_stats[k] = total
                            elif indicator == 'model-count':
                                if st.model_count is not None:
                                    total += st.model_count
                                monthly_stats[k] = total
                            elif indicator == 'level-average':
                                lev = []
                                if st.maturity_level is not None:
                                    lev.append(st.maturity_level)
                                level_avg = int(sum(lev) / len(lev))
                                monthly_stats[k] = level_avg
                    else:
                        monthly_stats[k] = 0
        for m, mv in monthly_stats.items():
            if max_count < mv:
                max_count = mv
        context['selected_quarter'] = self.kwargs['quarter']
        # context['year_stats'] = quarter_stats
        context['year_stats'] = monthly_stats
        context['max_count'] = max_count
        context['current_object'] = str('quarter/' + selected_quarter)
        context['active_filter'] = 'publication'
        context['active_indicator'] = indicator
        return context


class DatasetCategoryView(PermissionRequiredMixin, TemplateView):
    template_name = 'vitrina/datasets/dataset_categories.html'

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('dataset_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = DatasetCategoryForm(self.dataset)
        context['dataset'] = self.dataset
        return context

    def post(self, request, *args, **kwargs):
        form = DatasetCategoryForm(self.dataset, request.POST)
        if form.is_valid():
            self.dataset.category.clear()
            for category in form.cleaned_data.get('category'):
                self.dataset.category.add(category)
            self.dataset.save()
        else:
            messages.error(request, '\n'.join([error[0] for error in form.errors.values()]))
        return redirect(self.dataset.get_absolute_url())


class FilterCategoryView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        category_data = {}
        group_categories = []

        if group_id := request.GET.get('group_id'):
            group = get_object_or_404(DatasetGroup, pk=int(group_id))
            group_categories = group.category_set.all()
            categories = group_categories

        if ids := request.GET.get('category_ids'):
            ids = [int(i) for i in ids.split(',')]
            categories = categories.filter(pk__in=ids)

        if term := request.GET.get('term'):
            categories = categories.filter(title__icontains=term)

        for cat in categories:
            category_data[cat.pk] = {
                'show_checkbox': True,
            }
            for ancestor in cat.get_ancestors():
                if ancestor not in categories:
                    category_data[ancestor.pk] = {
                        'show_checkbox': True if ancestor in group_categories or not group_id else False,
                    }
        return JsonResponse({'categories': category_data})
