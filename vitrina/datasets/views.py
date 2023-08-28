import csv
import itertools
import json
import secrets
import uuid
from datetime import datetime, date
from collections import OrderedDict
from urllib.parse import urlencode

import pandas as pd
import numpy as np

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import QuerySet, Count, Max, Q, Sum
from django.db.models.functions import ExtractYear, ExtractMonth, ExtractQuarter, ExtractWeek
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
from vitrina.datasets.helpers import is_manager_dataset_list

from haystack.generic_views import FacetedSearchView
from parler.utils.context import switch_language
from parler.utils.i18n import get_language
from itsdangerous import URLSafeSerializer
from reversion import set_comment
from reversion.models import Version
from reversion.views import RevisionMixin

from parler.views import TranslatableUpdateView, TranslatableCreateView, LanguageChoiceMixin, ViewUrlMixin

from vitrina.api.models import ApiKey
from vitrina.plans.models import Plan, PlanDataset
from vitrina.projects.models import Project
from vitrina.comments.models import Comment
from vitrina.requests.models import Request, RequestObject
from vitrina.settings import ELASTIC_FACET_SIZE
from vitrina.statistics.models import DatasetStats, ModelDownloadStats
from vitrina.structure.models import Model, Metadata, Property
from vitrina.structure.services import create_structure_objects, get_model_name
from vitrina.structure.views import DatasetStructureMixin
from vitrina.tasks.models import Task
from vitrina.views import HistoryView, HistoryMixin, PlanMixin
from vitrina.datasets.forms import DatasetStructureImportForm, DatasetForm, DatasetSearchForm, AddProjectForm, \
    DatasetAttributionForm, DatasetCategoryForm, DatasetRelationForm, DatasetPlanForm, PlanForm, AddRequestForm
from vitrina.datasets.forms import DatasetMemberUpdateForm, DatasetMemberCreateForm
from vitrina.datasets.services import update_facet_data, get_projects
from vitrina.datasets.models import Dataset, DatasetStructure, DatasetGroup, DatasetAttribution, Type, DatasetRelation, \
    Relation, DatasetFile
from vitrina.datasets.structure import detect_read_errors, read
from vitrina.classifiers.models import Category, Frequency
from vitrina.helpers import get_selected_value, get_filter_url
from vitrina.helpers import Filter
from vitrina.helpers import DateFilter
from vitrina.orgs.helpers import is_org_dataset_list
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.resources.models import DatasetDistribution, Format
from vitrina.users.models import User
from vitrina.helpers import get_current_domain
import pytz


class DatasetListView(PlanMixin, FacetedSearchView):
    template_name = 'vitrina/datasets/list.html'
    facet_fields = [
        'status',
        'organization',
        'jurisdiction',
        'category',
        'parent_category',
        'groups',
        'frequency',
        'tags',
        'formats',
        'published',
        'level',
        'type',
    ]
    form_class = DatasetSearchForm
    max_num_facets = 20
    paginate_by = 20
    date_facet_fields = [
        {
            'field': 'published',
            'start_date': date(2019, 1, 1),
            'end_date': date.today(),
            'gap_by': 'month',
        },
    ]

    def get_queryset(self):
        datasets = super().get_queryset()

        sorting = self.request.GET.get('sort', None)

        options = {"size": ELASTIC_FACET_SIZE}
        for field in self.facet_fields:
            datasets = datasets.facet(field, **options)

        if is_manager_dataset_list(self.request):
            org_ids = [rep.object_id for rep in
                       self.request.user.representative_set.filter(role=Representative.MANAGER)]
            datasets = datasets.filter(organization__in=org_ids)

        if is_org_dataset_list(self.request):
            self.organization = get_object_or_404(
                Organization,
                pk=self.kwargs['pk'],
            )
            datasets = datasets.filter(organization=self.organization.pk)
        if sorting is None:
            datasets = datasets.order_by('-type_order', '-published')
        elif sorting == 'sort-by-date-newest':
            datasets = datasets.order_by('-published', '-type_order')
        elif sorting == 'sort-by-date-oldest':
            datasets = datasets.order_by('published', '-type_order')
        elif sorting == 'sort-by-title':
            if self.request.LANGUAGE_CODE == 'lt':
                datasets = datasets.order_by('lt_title_s', '-type_order')
            else:
                datasets = datasets.order_by('en_title_s', '-type_order')
        return datasets

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        datasets = self.get_queryset()
        facet_fields = context.get('facets').get('fields')
        date_facets = context['facets']['dates']
        form = context.get('form')
        sorting = self.request.GET.get('sort', None)
        filter_args = (self.request, form, facet_fields)
        extra_context = {
            'filters': [
                Filter(
                    *filter_args,
                    'status',
                    _("Rinkinio būsena"),
                    choices=Dataset.FILTER_STATUSES,
                    multiple=False,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    'level',
                    _("Brandos lygis"),
                    multiple=False,
                    is_int=True,
                ),
                Filter(
                    *filter_args,
                    'jurisdiction',
                    _("Valdymo sritis"),
                    Organization,
                    multiple=True,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    'organization',
                    _("Organizacija"),
                    Organization,
                    multiple=True,
                    is_int=False,
                ),
                Filter(
                    *filter_args,
                    'category',
                    _("Kategorija"),
                    Category,
                    multiple=True,
                    is_int=False,
                    parent='parent_category',
                ),
                Filter(
                    *filter_args,
                    'tags',
                    _("Žymė"),
                    Dataset,
                    multiple=True,
                    is_int=False,
                    display_method="get_tag_title"
                ),
                Filter(
                    *filter_args,
                    'frequency',
                    _("Atnaujinama"),
                    Frequency,
                    multiple=False,
                    is_int=True,
                ),
                Filter(
                    *filter_args,
                    'type',
                    _("Tipas"),
                    Type,
                    multiple=True,
                    is_int=False,
                    stats=False,
                ),
                Filter(
                    *filter_args,
                    'formats',
                    _("Formatas"),
                    multiple=True,
                    is_int=False,
                ),
                DateFilter(
                    self.request,
                    form,
                    date_facets,
                    'published',
                    _("Įkėlimo data"),
                    multiple=False,
                    is_int=False,
                ),
            ],
            'group_facet': update_facet_data(self.request, facet_fields, 'groups', DatasetGroup),
            'selected_groups': get_selected_value(form, 'groups', True, False),
            'q': form.cleaned_data.get('q', ''),
        }

        search_query_dict = dict(self.request.GET.copy())
        if 'query' in search_query_dict:
            search_query_dict.pop('query')
        context['search_query'] = search_query_dict

        sort_query_dict = dict(self.request.GET.copy())
        if 'sort' in sort_query_dict:
            sort_query_dict.pop('sort')
        sort_query = urlencode(sort_query_dict, True)

        if is_org_dataset_list(self.request):
            url = reverse('organization-datasets', args=[self.organization.pk])
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
            context['organization_id'] = self.organization.pk
        else:
            url = reverse('dataset-list')

        context['search_url'] = url
        context['sort_options'] = [
            {
                'title': "---------",
                'url':
                    f"{url}?{sort_query}" if sort_query else f"{url}",
                'icon': "fas fa-sort-amount-down-alt",
                'key': 'sort-by-default'
            },
            {
                'title': _("Naujausi"),
                'url':
                    f"{url}?{sort_query}&sort=sort-by-date-newest" if sort_query else f"{url}?sort=sort-by-date-newest",
                'icon': "fas fa-sort-amount-down-alt",
                'key': 'sort-by-date-newest'
             },
            {
                'title': _("Seniausi"),
                'url':
                    f"{url}?{sort_query}&sort=sort-by-date-oldest" if sort_query else f"{url}?sort=sort-by-date-oldest",
                'icon': "fas fa-sort-amount-up-alt",
                'key': 'sort-by-date-oldest'
            },
            {
                'title': _("Pagal pavadinimą"),
                'url':
                    f"{url}?{sort_query}&sort=sort-by-title" if sort_query else f"{url}?sort=sort-by-title",
                'icon': "fas fa-sort-amount-down-alt",
                'key': 'sort-by-title'
            },
        ]

        context.update(extra_context)
        context['sort'] = sorting
        return context

    def get_plan_url(self):
        if is_org_dataset_list(self.request):
            return reverse('organization-plans', args=[self.organization.pk])
        else:
            return None


class DatasetDetailView(
    LanguageChoiceMixin,
    HistoryMixin,
    DatasetStructureMixin,
    PlanMixin,
    DetailView
):
    model = Dataset
    template_name = 'vitrina/datasets/detail.html'
    context_object_name = 'dataset'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'
    plan_url_name = 'dataset-plans'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        dataset = context_data.get('dataset')
        organization = get_object_or_404(Organization, id=dataset.organization.pk)
        extra_context_data = {
            'tags': dataset.get_tag_object_list(),
            'subscription': [],
            'status': dataset.get_status_display(),
            # TODO: harvested functionality needs to be implemented
            'harvested': '',
            'can_add_resource': has_perm(self.request.user, Action.CREATE, DatasetDistribution, dataset),
            'can_update_dataset': has_perm(self.request.user, Action.UPDATE, dataset),
            'can_view_members': has_perm(self.request.user, Action.VIEW, Representative, dataset),
            'resources': dataset.datasetdistribution_set.all(),
            'org_logo': organization.image,
            'attributions': dataset.datasetattribution_set.order_by('attribution'),
        }
        part_of = dataset.part_of.order_by('relation')
        part_of = itertools.groupby(part_of, lambda x: x.relation)
        extra_context_data['part_of'] = [(relation, list(values)) for relation, values in part_of]
        related_datasets = dataset.related_datasets.all()
        related_datasets = itertools.groupby(related_datasets, lambda x: x.relation)
        extra_context_data['related_datasets'] = [(relation, list(values)) for relation, values in related_datasets]

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
        context['service_types'] = list(Type.objects.filter(name=Type.SERVICE).values_list('pk', flat=True))
        return context

    def get(self, request, *args, **kwargs):
        return super(DatasetCreateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=True)
        self.object.slug = slugify(self.object.title)
        self.object.organization_id = self.kwargs.get('pk')

        types = form.cleaned_data.get('type')
        self.object.type.set(types)
        if types.filter(name=Type.SERVICE):
            self.object.service = True
        else:
            self.object.endpoint_url = None
            self.object.endpoint_type = None
            self.object.endpoint_description = None
            self.object.endpoint_description_type = None
            self.object.service = False
        if types.filter(name=Type.SERIES):
            self.object.series = True
        else:
            self.object.series = False

        self.object.save()
        set_comment(Dataset.CREATED)

        for file in form.cleaned_data.get('files', []):
            DatasetFile.objects.get_or_create(
                dataset=self.object,
                file=file,
            )

        Metadata.objects.create(
            uuid=str(uuid.uuid4()),
            dataset=self.object,
            content_type=ContentType.objects.get_for_model(self.object),
            object_id=self.object.pk,
            name=form.cleaned_data.get('name'),
            prepare_ast={},
            version=1,
        )

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
        context['service_types'] = list(Type.objects.filter(name=Type.SERVICE).values_list('pk', flat=True))
        return context

    def get(self, request, *args, **kwargs):
        return super(DatasetUpdateView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.slug = slugify(self.object.title)
        tags = form.cleaned_data['tags']
        self.object.tags.set(tags)

        types = form.cleaned_data.get('type')
        self.object.type.set(types)
        if types.filter(name=Type.SERVICE):
            self.object.service = True
        else:
            self.object.endpoint_url = None
            self.object.endpoint_type = None
            self.object.endpoint_description = None
            self.object.endpoint_description_type = None
            self.object.service = False
        if types.filter(name=Type.SERIES):
            self.object.series = True
        else:
            self.object.series = False

        self.object.save()
        set_comment(Dataset.EDITED)

        if 'files' in form.changed_data:
            for file in form.cleaned_data.get('files', []):
                DatasetFile.objects.get_or_create(
                    dataset=self.object,
                    file=file,
                )

        if 'name' in form.changed_data:
            if metadata := self.object.metadata.first():
                metadata.name = form.cleaned_data.get('name')
                metadata.save()
            else:
                Metadata.objects.create(
                    uuid=str(uuid.uuid4()),
                    dataset=self.object,
                    content_type=ContentType.objects.get_for_model(self.object),
                    object_id=self.object.pk,
                    name=form.cleaned_data.get('name'),
                    prepare_ast={},
                    version=1,
                )

            # Update model names
            for model in self.object.model_set.all():
                if model_meta := model.metadata.first():
                    model_meta.name = get_model_name(self.object, model.name)
                    model_meta.save()

        return HttpResponseRedirect(self.get_success_url())


class DatasetHistoryView(DatasetStructureMixin, PlanMixin, HistoryView):
    model = Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-history"
    plan_url_name = 'dataset-plans'
    tabs_template_name = 'vitrina/datasets/tabs.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.object.pk]): self.object.title,
        }
        return context

    def get_history_objects(self):
        model_ids = self.models.values_list('pk', flat=True)
        if self.can_manage_structure:
            property_ids = Property.objects.filter(
                model__pk__in=model_ids,
                given=True
            ).values_list('pk', flat=True)
        else:
            property_ids = Property.objects.filter(
                model__pk__in=model_ids,
                given=True,
                metadata__access__gte=Metadata.PUBLIC,
            ).values_list('pk', flat=True)

        property_history_objects = Version.objects.get_for_model(Property).filter(object_id__in=list(property_ids))
        model_history_objects = Version.objects.get_for_model(Model).filter(object_id__in=list(model_ids))
        dataset_history_objects = Version.objects.get_for_object(self.object)
        history_objects = property_history_objects | model_history_objects | dataset_history_objects
        return history_objects.order_by('-revision__date_created')


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
    PlanMixin,
    DatasetStructureMixin,
    ListView,
):
    model = Representative
    template_name = 'vitrina/datasets/members_list.html'
    context_object_name = 'members'
    paginate_by = 20

    # HistoryMixin
    object: Dataset
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'
    plan_url_name = 'dataset-plans'

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
    DatasetStructureMixin,
    HistoryMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Representative
    form_class = DatasetMemberCreateForm
    template_name = 'base_form.html'

    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tabs'] = 'vitrina/datasets/tabs.html'
        context['can_view_members'] = self.has_permission()
        context['representative_url'] = reverse('dataset-members', args=[self.dataset.pk])
        context['current_title'] = _("Tvarkytojo pridėjimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def get_detail_object(self):
        return self.dataset

    def get_history_object(self):
        return self.dataset

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

            if not user.organization:
                user.organization = self.dataset.organization
                user.save()
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
    DatasetStructureMixin,
    HistoryMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Representative
    form_class = DatasetMemberUpdateForm
    template_name = 'base_form.html'
    pk_url_kwarg = 'representative_id'

    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'

    def has_permission(self):
        representative = get_object_or_404(
            Representative,
            pk=self.kwargs.get('representative_id'),
        )
        return has_perm(self.request.user, Action.UPDATE, representative)

    def get_success_url(self):
        return reverse('dataset-members', kwargs={
            'pk': self.kwargs.get('pk'),
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tabs'] = 'vitrina/datasets/tabs.html'
        context['can_view_members'] = self.has_permission()
        context['representative_url'] = reverse('dataset-members', args=[self.dataset.pk])
        context['current_title'] = _("Tvarkytojo redagavimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def get_detail_object(self):
        return self.dataset

    def get_history_object(self):
        return self.dataset

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

        if not self.object.user.organization:
            self.object.user.organization = self.dataset.organization
            self.object.user.save()

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


class DatasetProjectsView(
    DatasetStructureMixin,
    HistoryMixin,
    PlanMixin,
    ListView
):
    model = Project
    template_name = 'vitrina/datasets/project_list.html'
    context_object_name = 'projects'
    paginate_by = 20

    # HistroyMixin
    object: Dataset
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'
    plan_url_name = 'dataset-plans'

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


class DatasetRequestsView(DatasetStructureMixin, HistoryMixin, PlanMixin, ListView):
    model = RequestObject
    template_name = 'vitrina/datasets/request_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    # HistoryMixin
    object: Dataset
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-history'
    plan_url_name = 'dataset-plans'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Dataset, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        model_ids = Model.objects.filter(dataset=self.object).values_list('pk', flat=True)
        property_ids = Property.objects.filter(model__pk__in=model_ids).values_list('pk', flat=True)
        return RequestObject.objects.filter(
            Q(
                content_type=ContentType.objects.get_for_model(self.object),
                object_id=self.object.pk
            ) | Q(
                content_type=ContentType.objects.get_for_model(Model),
                object_id__in=model_ids
            ) | Q(
                content_type=ContentType.objects.get_for_model(Property),
                object_id__in=property_ids
            )
        ).order_by('-request__created', 'request__status')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.object
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.object,
        )
        return context


class AddRequestView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView,
):
    model = Dataset
    form_class = AddRequestForm
    template_name = 'base_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get_form_kwargs(self):
        kwargs = super(AddRequestView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        kwargs.update({'dataset': self.dataset})
        return kwargs

    def form_valid(self, form):
        super().form_valid(form)
        for request in form.cleaned_data['requests']:
            RequestObject.objects.create(request=request, object_id=self.object.pk,
                                         content_type=ContentType.objects.get_for_model(self.object))
        Task.objects.create(
            title=f"Poreikis duomenų rinkiniui: {self.dataset}",
            description=f"Sukurtas naujas poreikis duomenų rinkiniui: {self.dataset}.",
            content_type=ContentType.objects.get_for_model(self.dataset),
            object_id=self.dataset.pk,
            organization=Organization.objects.get(pk=self.dataset.organization_id),
            status=Task.CREATED,
            user=self.request.user,
            type=Task.REQUEST
        )
        set_comment(Dataset.REQUEST_SET)
        self.object.save()
        return HttpResponseRedirect(
            reverse('dataset-requests', kwargs={'pk': self.object.pk})
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_title'] = self.dataset
        context['parent_url'] = self.dataset.get_absolute_url()
        context['current_title'] = _('Poreikių pridėjimas')
        return context


class RemoveRequestView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Dataset
    template_name = 'confirm_remove.html'

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=self.kwargs.get('pk'))
        self.request_object = get_object_or_404(RequestObject, pk=self.kwargs.get('request_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.request_object)

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse('dataset-requests', kwargs={'pk': self.dataset.pk}))

    def delete(self, request, *args, **kwargs):
        Comment.objects.filter(
            rel_object_id=self.request_object.request.pk,
            rel_content_type=ContentType.objects.get_for_model(self.request_object.request)
        ).delete()
        self.request_object.delete()
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        return reverse('dataset-requests', kwargs={'pk': self.dataset.pk})


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


Y_TITLES = {
    'download-request-count': _('Atsisiuntimų (užklausų) skaičius'),
    'download-object-count': _('Atsisiuntimų (objektų) skaičius'),
    'object-count': _('Objektų skaičius'),
    'field-count': _('Savybių (duomenų laukų) skaičius'),
    'model-count': _('Esybių (modelių) skaičius'),
    'distribution-count': _('Duomenų šaltinių (distribucijų) skaičius'),
    'dataset-count': _('Duomenų rinkinių skaičius'),
    'request-count': _('Poreikių skaičius'),
    'project-count': _('Projektų skaičius'),
    'level-average': _('Brandos lygis')
}

DATASET_INDICATOR_FIELDS = {
    'object-count': 'object_count',
    'field-count': 'field_count',
    'model-count': 'model_count',
    'distribution-count': 'distribution_count',
    'request-count': 'request_count',
    'project-count': 'project_count',
    'level-average': 'maturity_level'
}

MODEL_INDICATOR_FIELDS = {
    'download-request-count': 'model_requests',
    'download-object-count': 'model_objects',
}


class DatasetStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/status.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = Dataset.objects.all().first().created
        statuses = {}
        stat_groups = {}
        chart_data = []

        status_translations = {'HAS_STRUCTURE': 'Įkelta duomenų struktūra',
                               'STRUCTURED': 'Įkelta duomenų struktūra',
                               'HAS_DATA': 'Atverti duomenys',
                               'OPENED': 'Atverti duomenys',
                               'INVENTORED': 'Inventorintas',
                               'UNASSIGNED': 'Nepriskirtas'}

        most_recent_comments = Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id__in=datasets.values_list('pk', flat=True),
            status__isnull=False).values('object_id') \
            .annotate(latest_status_change=Max('created')).values('object_id', 'latest_status_change') \
            .order_by('latest_status_change')

        dataset_status = Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id__in=most_recent_comments.values('object_id'),
            created__in=most_recent_comments.values('latest_status_change')) \
            .annotate(year=ExtractYear('created'), month=ExtractMonth('created')) \
            .values('object_id', 'status', 'year', 'month')

        comm_statuses = dataset_status.order_by('status').values_list('status', flat=True).distinct()

        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

        for d in datasets:
            if d.status is not None:
                statuses[d.status] = statuses.get(d.status, 0) + 1
        keys = list(statuses.keys())
        if indicator != 'dataset-count':
            for k in keys:
                id_list = []
                for d in datasets:
                    if d.status == k:
                        id_list.append(d.pk)
                stat_groups[k] = id_list
            for item in stat_groups.keys():
                if indicator == 'download-request-count' or indicator == 'download-object-count':
                    models = Model.objects.filter(dataset_id__in=stat_groups[item]).values_list('metadata__name',
                                                                                                flat=True)
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
                                level_avg = int(sum(lev) / len(lev))
                                statuses[item] = level_avg
        values = list(statuses.values())
        for v in values:
            if max_count < int(v):
                max_count = int(v)
        if sorting == 'sort-desc':
            sorted_value_index = np.flip(np.argsort(values))
        else:
            sorted_value_index = np.argsort(values)
        sorted_statuses = {keys[i]: values[i] for i in sorted_value_index}

        sort = 0
        for status in statuses:
            sort += 1
            total = 0
            temp = []
            for label in labels:
                if indicator == 'dataset-count':
                    if status == 'HAS_DATA':
                        comm_val = 'OPENED'
                    elif status == 'HAS_STRUCTURE':
                        comm_val = 'STRUCTURED'
                    else:
                        comm_val = 'INVENTORED'
                    total += dataset_status.filter(status=comm_val, year=label.year) \
                        .values('object_id') \
                        .annotate(count=Count('object_id', distinct=True)) \
                        .count()

                elif indicator == 'download-request-count' or indicator == 'download-object-count':
                    models = Model.objects.filter(dataset_id__in=stat_groups[status]).values_list('metadata__name',
                                                                                                  flat=True)
                    per_datasets = 0
                    if len(models) > 0:
                        for m in models:
                            model_stats = ModelDownloadStats.objects.filter(model=m)
                            if len(model_stats) > 0:
                                for m_st in model_stats:
                                    if indicator == 'download-request-count':
                                        if m_st is not None:
                                            per_datasets += m_st.model_requests
                                    elif indicator == 'download-object-count':
                                        if m_st is not None:
                                            per_datasets += m_st.model_objects
                            total = per_datasets

                else:
                    if status in stat_groups:
                        ids = stat_groups[status]
                        stat = DatasetStats.objects.filter(dataset_id__in=ids, created__year=label.year)
                        per_datasets = 0
                        if len(stat) > 0:
                            for st in stat:
                                if indicator == 'request-count':
                                    if st.request_count is not None:
                                        per_datasets += st.request_count
                                elif indicator == 'project-count':
                                    if st.project_count is not None:
                                        per_datasets += st.project_count
                                elif indicator == 'distribution-count':
                                    if st.distribution_count is not None:
                                        per_datasets += st.distribution_count
                                elif indicator == 'object-count':
                                    if st.object_count is not None:
                                        per_datasets += st.object_count
                                elif indicator == 'field-count':
                                    if st.field_count is not None:
                                        per_datasets += st.field_count
                                elif indicator == 'model-count':
                                    if st.model_count is not None:
                                        per_datasets += st.model_count
                                elif indicator == 'level-average':
                                    lev = []
                                    if st.maturity_level is not None:
                                        lev.append(st.maturity_level)
                                    level_avg = int(sum(lev) / len(lev))
                                    per_datasets = level_avg

                        total = per_datasets
                if frequency == 'W':
                    temp.append({'x': _date(label.start_time, ff), 'y': total})
                else:
                    temp.append({'x': _date(label, ff), 'y': total})
            dt = {
                'label': str(status_translations[status]),
                'data': temp,
                'borderWidth': 1,
                'fill': True,
                'sort': sort
            }
            chart_data.append(dt)

        chart_data = sorted(chart_data, key=lambda x: x['sort'])

        context['data'] = json.dumps(chart_data)
        context['graph_title'] = _('Rodiklis pagal rinkinio būseną laike')
        context['yAxis_title'] = Y_TITLES[indicator]
        context['xAxis_title'] = _('Laikas')
        context['status_data'] = sorted_statuses
        context['max_count'] = max_count
        context['duration'] = duration
        context['active_filter'] = 'status'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        return context


class DatasetManagementsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/jurisdictions.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facet_fields = context.get('facets').get('fields')
        all_orgs = update_facet_data(self.request, facet_fields, 'jurisdiction', Organization)
        all_orgs = sorted(all_orgs, key=lambda jur: jur['count'], reverse=True)
        top_jurisdictions = sorted(all_orgs, key=lambda jur: jur['count'], reverse=True)[:10]

        start_date = Dataset.objects.all().first().created
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        jurisdiction_data = []
        chart_data = []
        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

        datasets = context['object_list']

        for jurisdiction in all_orgs:
            count = 0
            data = []
            statistics = []
            jurisdiction_dataset_ids = datasets.filter(
                jurisdiction=jurisdiction['filter_value']
            ).values_list('pk', flat=True)
            jurisdiction_datasets = Dataset.public.filter(pk__in=jurisdiction_dataset_ids)

            if DATASET_INDICATOR_FIELDS.get(indicator):
                statistic_ids = DatasetStats.objects.filter(
                    dataset_id__in=jurisdiction_dataset_ids
                ).order_by(
                    'dataset_id',
                    '-created'
                ).distinct(
                    'dataset_id'
                ).values_list(
                            'pk', flat=True)
                statistics = DatasetStats.objects.filter(pk__in=statistic_ids)
            elif MODEL_INDICATOR_FIELDS.get(indicator):
                model_names = Metadata.objects.filter(
                    content_type=ContentType.objects.get_for_model(Model),
                    dataset__pk__in=jurisdiction_dataset_ids
                ).values_list('name', flat=True)
                statistics = ModelDownloadStats.objects.filter(
                    model__in=model_names
                )

            for label in labels:

                if indicator == 'dataset-count':
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        jurisdiction_datasets,
                        'created'
                    )
                elif field := DATASET_INDICATOR_FIELDS.get(indicator):
                    #todo pasidomėti ar čia taip iš tiesų
                    count = get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    ) or count
                elif field := MODEL_INDICATOR_FIELDS.get(indicator):
                    #todo pasidomėti ar čia taip iš tiesų
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    )

                if frequency == 'W':
                    data.append({'x': _date(label.start_time, ff), 'y': count})
                else:
                    data.append({'x': _date(label, ff), 'y': count})

            if jurisdiction in top_jurisdictions:
                dt = {
                    'label': jurisdiction['display_value'],
                    'data': data,
                    'borderWidth': 1,
                    'fill': True,
                }
                chart_data.append(dt)

            if data:
                jurisdiction['count'] = data[-1]['y']
            else:
                jurisdiction['count'] = 0
            jurisdiction_data.append(jurisdiction)

        if sorting == 'sort-desc':
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'], reverse=True)
            jurisdiction_data = sorted(jurisdiction_data, key=lambda x: x['count'], reverse=True)
        else:
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'])
            jurisdiction_data = sorted(jurisdiction_data, key=lambda x: x['count'])

        max_count = max([x['count'] for x in jurisdiction_data]) if jurisdiction_data else 0

        context['jurisdiction_data'] = jurisdiction_data
        context['max_count'] = max_count
        context['active_filter'] = 'jurisdiction'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        context['data'] = json.dumps(chart_data)
        context['graph_title'] = _('Rodiklis pagal rinkinio valdymo sritį laike')
        context['yAxis_title'] = Y_TITLES[indicator]
        context['xAxis_title'] = _('Laikas')
        context['duration'] = duration

        return context


def get_count_by_frequency(
        frequency,
        label,
        queryset,
        field,
        aggregate_field=None,
):
    if frequency == 'Y':
        query = {
            f"{field}__year": label.year
        }
    elif frequency == 'Q':
        queryset = queryset.annotate(
            quarter=ExtractQuarter('created')
        )
        query = {
            f"{field}__year": label.year,
            "quarter": label.quarter
        }
    elif frequency == 'M':
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month
        }
    elif frequency == 'W':
        queryset = queryset.annotate(
            week=ExtractWeek('created')
        )
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month,
            "week": label.week
        }
    else:
        query = {
            f"{field}__year": label.year,
            f"{field}__month": label.month,
            f"{field}__day": label.day
        }

    if aggregate_field:
        return queryset.filter(**query).aggregate(
            Sum(aggregate_field)
        )[f"{aggregate_field}__sum"] or 0
    else:
        return queryset.filter(**query).count()


def get_frequency_and_format(duration):
    if duration == 'duration-yearly':
        frequency = 'Y'
        ff = 'Y'
    elif duration == 'duration-quarterly':
        frequency = 'Q'
        ff = 'Y M'
    elif duration == 'duration-monthly':
        frequency = 'M'
        ff = 'Y m'
    elif duration == 'duration-weekly':
        frequency = 'W'
        ff = 'Y W'
    else:
        frequency = 'D'
        ff = 'Y m d'
    return frequency, ff


class DatasetsLevelView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/level.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        datasets = context['object_list']
        facet_fields = context.get('facets').get('fields')
        levels = update_facet_data(self.request, facet_fields, 'level', None)

        start_date = Dataset.objects.all().first().created
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        level_data = []
        chart_data = []
        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

        for level in levels:
            count = 0
            data = []
            statistics = []
            level_dataset_ids = datasets.filter(
                level=level['filter_value']
            ).values_list('pk', flat=True)
            level_datasets = Dataset.public.filter(pk__in=level_dataset_ids)

            if DATASET_INDICATOR_FIELDS.get(indicator):
                statistic_ids = DatasetStats.objects.filter(
                    dataset_id__in=level_dataset_ids
                ).order_by(
                    'dataset_id',
                    '-created'
                ).distinct(
                    'dataset_id'
                ).values_list(
                    'pk', flat=True)
                statistics = DatasetStats.objects.filter(pk__in=statistic_ids)
            elif MODEL_INDICATOR_FIELDS.get(indicator):
                model_names = Metadata.objects.filter(
                    content_type=ContentType.objects.get_for_model(Model),
                    dataset__pk__in=level_dataset_ids
                ).values_list('name', flat=True)
                statistics = ModelDownloadStats.objects.filter(
                    model__in=model_names
                )

            for label in labels:

                if indicator == 'dataset-count':
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        level_datasets,
                        'created'
                    )
                elif field := DATASET_INDICATOR_FIELDS.get(indicator):
                    count = get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    ) or count
                elif field := MODEL_INDICATOR_FIELDS.get(indicator):
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    )

                if frequency == 'W':
                    data.append({'x': _date(label.start_time, ff), 'y': count})
                else:
                    data.append({'x': _date(label, ff), 'y': count})

            dt = {
                'label': "★" * level['filter_value'],
                'data': data,
                'borderWidth': 1,
                'fill': True,
            }
            chart_data.append(dt)

            if data:
                level['count'] = data[-1]['y']
            else:
                level['count'] = 0
            level_data.append(level)

        if sorting == 'sort-desc':
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'], reverse=True)
            level_data = sorted(level_data, key=lambda x: x['count'], reverse=True)
        else:
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'])
            level_data = sorted(level_data, key=lambda x: x['count'])

        max_count = max([x['count'] for x in level_data]) if level_data else 0

        context['level_data'] = level_data
        context['max_count'] = max_count
        context['active_filter'] = 'level'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        context['data'] = json.dumps(chart_data)
        context['graph_title'] = _('Rodiklis pagal rinkinio brandos lygį laike')
        context['yAxis_title'] = Y_TITLES[indicator]
        context['xAxis_title'] = _('Laikas')
        context['duration'] = duration

        return context


class DatasetsOrganizationsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/organizations.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facet_fields = context.get('facets').get('fields')
        all_orgs = update_facet_data(self.request, facet_fields, 'organization', Organization)
        all_orgs = sorted(all_orgs, key=lambda org: org['count'], reverse=True)
        top_orgs = sorted(all_orgs, key=lambda org: org['count'], reverse=True)[:10]

        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = Dataset.objects.all().first().created
        org_data = []
        chart_data = []
        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

        for org in all_orgs:
            count = 0
            data = []
            statistics = []
            org_dataset_ids = datasets.filter(
                organization=org['filter_value']
            ).values_list('pk', flat=True)
            org_datasets = Dataset.public.filter(pk__in=org_dataset_ids)

            if DATASET_INDICATOR_FIELDS.get(indicator):
                statistic_ids = DatasetStats.objects.filter(
                    dataset_id__in=org_dataset_ids
                ).order_by(
                    'dataset_id',
                    '-created'
                ).distinct(
                    'dataset_id'
                ).values_list(
                    'pk', flat=True
                )
                statistics = DatasetStats.objects.filter(pk__in=statistic_ids)
            elif MODEL_INDICATOR_FIELDS.get(indicator):
                model_names = Metadata.objects.filter(
                    content_type=ContentType.objects.get_for_model(Model),
                    dataset__pk__in=org_dataset_ids
                ).values_list('name', flat=True)
                statistics = ModelDownloadStats.objects.filter(
                    model__in=model_names
                )

            for label in labels:
                if indicator == 'dataset-count':
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        org_datasets,
                        'created'
                    )
                elif field := DATASET_INDICATOR_FIELDS.get(indicator):
                    #todo pasidomėti ar čia taip iš tiesų
                    count = get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    ) or count
                elif field := MODEL_INDICATOR_FIELDS.get(indicator):
                    #todo pasidomėti ar čia taip iš tiesų
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    )

                if frequency == 'W':
                    data.append({'x': _date(label.start_time, ff), 'y': count})
                else:
                    data.append({'x': _date(label, ff), 'y': count})

            if org in top_orgs:
                dt = {
                    'label': org['display_value'],
                    'data': data,
                    'borderWidth': 1,
                    'fill': True,
                }
                chart_data.append(dt)

            if data:
                org['count'] = data[-1]['y']
            else:
                org['count'] = 0
            org_data.append(org)

        if sorting == 'sort-desc':
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'], reverse=True)
            org_data = sorted(org_data, key=lambda x: x['count'], reverse=True)
        else:
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'])
            org_data = sorted(org_data, key=lambda x: x['count'])

        max_count = max([x['count'] for x in org_data]) if org_data else 0

        context['organization_data'] = org_data
        context['max_count'] = max_count
        context['active_filter'] = 'organizations'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        context['data'] = json.dumps(chart_data)
        context['graph_title'] = _('Rodiklis pagal rinkinio būseną laike')
        context['yAxis_title'] = Y_TITLES[indicator]
        context['xAxis_title'] = _('Laikas')
        context['duration'] = duration
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
        facet_fields = context.get('facets').get('fields')
        all_tags = update_facet_data(self.request, facet_fields, 'tags', None)
        all_tags = sorted(all_tags, key=lambda tag: tag['count'], reverse=True)
        top_tags = sorted(all_tags, key=lambda tag: tag['count'], reverse=True)[:10]

        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = Dataset.objects.all().first().created
        tag_data = []
        chart_data = []
        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

        for tag in all_tags:
            count = 0
            data = []
            statistics = []
            tag_ids = datasets.filter(
                tags=tag['filter_value']
            ).values_list('pk', flat=True)
            tag_datasets = Dataset.public.filter(pk__in=tag_ids)

            dataset = Dataset.objects.filter(pk=tag_ids[0]).get()
            t_title = dataset.get_tag_title(tag['filter_value'])
            tag.update({'title': t_title})

            if DATASET_INDICATOR_FIELDS.get(indicator):
                statistic_ids = DatasetStats.objects.filter(
                    dataset_id__in=tag_ids
                ).order_by(
                    'dataset_id',
                    '-created'
                ).distinct(
                    'dataset_id'
                ).values_list(
                    'pk', flat=True
                )
                statistics = DatasetStats.objects.filter(pk__in=statistic_ids)
            elif MODEL_INDICATOR_FIELDS.get(indicator):
                model_names = Metadata.objects.filter(
                    content_type=ContentType.objects.get_for_model(Model),
                    dataset__pk__in=tag_ids
                ).values_list('name', flat=True)
                statistics = ModelDownloadStats.objects.filter(
                    model__in=model_names
                )

            for label in labels:
                if indicator == 'dataset-count':
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        tag_datasets,
                        'created'
                    )
                elif field := DATASET_INDICATOR_FIELDS.get(indicator):
                    # todo pasidomėti ar čia taip iš tiesų
                    count = get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    ) or count
                elif field := MODEL_INDICATOR_FIELDS.get(indicator):
                    # todo pasidomėti ar čia taip iš tiesų
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    )

                if frequency == 'W':
                    data.append({'x': _date(label.start_time, ff), 'y': count})
                else:
                    data.append({'x': _date(label, ff), 'y': count})

            if tag in top_tags:
                dt = {
                    'label': t_title,
                    'data': data,
                    'borderWidth': 1,
                    'fill': True,
                }
                chart_data.append(dt)

            if data:
                tag['count'] = data[-1]['y']
            else:
                tag['count'] = 0
            tag_data.append(tag)

        if sorting == 'sort-desc':
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'], reverse=True)
            tag_data = sorted(tag_data, key=lambda x: x['count'], reverse=True)
        else:
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'])
            tag_data = sorted(tag_data, key=lambda x: x['count'])

        max_count = max([x['count'] for x in tag_data]) if tag_data else 0

        context['tag_data'] = tag_data
        context['max_count'] = max_count
        context['active_filter'] = 'tag'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        context['data'] = json.dumps(chart_data)
        context['graph_title'] = _('Rodiklis pagal rinkinio būseną laike')
        context['yAxis_title'] = Y_TITLES[indicator]
        context['xAxis_title'] = _('Laikas')
        context['duration'] = duration
        return context


class DatasetsFormatView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/formats.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facet_fields = context.get('facets').get('fields')
        all_formats = update_facet_data(self.request, facet_fields, 'formats', None)
        all_formats = sorted(all_formats, key=lambda format: format['count'], reverse=True)
        top_formats = sorted(all_formats, key=lambda format: format['count'], reverse=True)[:10]

        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = Dataset.objects.all().first().created
        format_data = []
        chart_data = []
        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

        for format in all_formats:
            count = 0
            data = []
            statistics = []
            format_ids = datasets.filter(
                formats=format['filter_value']
            ).values_list('pk', flat=True)
            tag_datasets = Dataset.public.filter(pk__in=format_ids)

            if DATASET_INDICATOR_FIELDS.get(indicator):
                statistic_ids = DatasetStats.objects.filter(
                    dataset_id__in=format_ids
                ).order_by(
                    'dataset_id',
                    '-created'
                ).distinct(
                    'dataset_id'
                ).values_list(
                    'pk', flat=True
                )
                statistics = DatasetStats.objects.filter(pk__in=statistic_ids)
            elif MODEL_INDICATOR_FIELDS.get(indicator):
                model_names = Metadata.objects.filter(
                    content_type=ContentType.objects.get_for_model(Model),
                    dataset__pk__in=format_ids
                ).values_list('name', flat=True)
                statistics = ModelDownloadStats.objects.filter(
                    model__in=model_names
                )

            for label in labels:
                if indicator == 'dataset-count':
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        tag_datasets,
                        'created'
                    )
                elif field := DATASET_INDICATOR_FIELDS.get(indicator):
                    # todo pasidomėti ar čia taip iš tiesų
                    count = get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    ) or count
                elif field := MODEL_INDICATOR_FIELDS.get(indicator):
                    # todo pasidomėti ar čia taip iš tiesų
                    count += get_count_by_frequency(
                        frequency,
                        label,
                        statistics,
                        'created',
                        field
                    )

                if frequency == 'W':
                    data.append({'x': _date(label.start_time, ff), 'y': count})
                else:
                    data.append({'x': _date(label, ff), 'y': count})

            if format in top_formats:
                dt = {
                    'label': format['display_value'],
                    'data': data,
                    'borderWidth': 1,
                    'fill': True,
                }
                chart_data.append(dt)

            if data:
                format['count'] = data[-1]['y']
            else:
                format['count'] = 0
            format_data.append(format)

        if sorting == 'sort-desc':
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'], reverse=True)
            format_data = sorted(format_data, key=lambda x: x['count'], reverse=True)
        else:
            chart_data = sorted(chart_data, key=lambda x: x['data'][-1]['y'])
            format_data = sorted(format_data, key=lambda x: x['count'])

        max_count = max([x['count'] for x in format_data]) if format_data else 0

        context['format_data'] = format_data
        context['max_count'] = max_count
        context['active_filter'] = 'format'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        context['data'] = json.dumps(chart_data)
        context['graph_title'] = _('Rodiklis pagal rinkinio būseną laike')
        context['yAxis_title'] = Y_TITLES[indicator]
        context['xAxis_title'] = _('Laikas')
        context['duration'] = duration
        return context


class DatasetsFrequencyView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/frequency.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        facet_fields = context.get('facets').get('fields')
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = Dataset.objects.all().first().created
        frequencies = {}
        stat_groups = {}
        chart_data = []

        top_freqs = update_facet_data(self.request, facet_fields, 'frequency', None)
        sorted_top_freqs = sorted(top_freqs, key=lambda cat: cat['count'], reverse=True)[:10]

        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

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
                    models = Model.objects.filter(dataset_id__in=stat_groups[item]).values_list('metadata__name',
                                                                                                flat=True)
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
        if sorting == 'sort-desc':
            sorted_value_index = np.flip(np.argsort(values))
        else:
            sorted_value_index = np.argsort(values)
        sorted_frequencies = {keys[i]: values[i] for i in sorted_value_index}

        sort = 0
        for index, f in enumerate(sorted_top_freqs):
            sort += 1
            freq = Frequency.objects.get(pk=f['filter_value'])
            dataset_ids = Dataset.objects.filter(frequency=freq).values_list('pk', flat=True)
            total = 0
            temp = []
            for label in labels:
                if indicator == 'dataset-count':
                    total += Dataset.objects.filter(frequency=freq, created__year=label.year).count()
                else:
                    stat = DatasetStats.objects.filter(dataset_id__in=dataset_ids, created__year=label.year)
                    per_datasets = 0
                    if len(stat) > 0:
                        for st in stat:
                            if indicator == 'request-count':
                                if st.request_count is not None:
                                    per_datasets += st.request_count
                            elif indicator == 'project-count':
                                if st.project_count is not None:
                                    per_datasets += st.project_count
                            elif indicator == 'distribution-count':
                                if st.distribution_count is not None:
                                    per_datasets += st.distribution_count
                            elif indicator == 'object-count':
                                if st.object_count is not None:
                                    per_datasets += st.object_count
                            elif indicator == 'field-count':
                                if st.field_count is not None:
                                    per_datasets += st.field_count
                            elif indicator == 'model-count':
                                if st.model_count is not None:
                                    per_datasets += st.model_count
                            elif indicator == 'level-average':
                                lev = []
                                if st.maturity_level is not None:
                                    lev.append(st.maturity_level)
                                level_avg = int(sum(lev) / len(lev))
                                per_datasets = level_avg

                    total = per_datasets
                if frequency == 'W':
                    temp.append({'x': _date(label.start_time, ff), 'y': total})
                else:
                    temp.append({'x': _date(label, ff), 'y': total})
            dt = {
                'label': f['display_value'],
                'data': temp,
                'borderWidth': 1,
                'fill': True,
                'sort': sort
            }
            chart_data.append(dt)

        chart_data = sorted(chart_data, key=lambda x: x['sort'])

        context['data'] = json.dumps(chart_data)
        context['graph_title'] = _('Rodiklis pagal rinkinio būseną laike')
        context['yAxis_title'] = Y_TITLES[indicator]
        context['xAxis_title'] = _('Laikas')
        context['frequency_data'] = sorted_frequencies
        context['max_count'] = max_count
        context['duration'] = duration
        context['active_filter'] = 'frequency'
        context['active_indicator'] = indicator
        context['sort'] = sorting
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
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        filtered_orgs = []

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
                if sorting == 'sort-asc':
                    single_dict = sorted(single_dict, key=lambda dd: dd['count'], reverse=False)
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
            if sorting == 'sort-desc':
                result = sorted(result, key=lambda dd: dd['count'], reverse=True)
            else:
                result = sorted(result, key=lambda dd: dd['count'], reverse=False)
            # result = sorted(result, key=lambda dd: dd['count'], reverse=True)
        context['single_org'] = True
        context['jurisdiction_data'] = result
        context['max_count'] = max_count
        context['current_object'] = self.kwargs.get('pk')
        context['active_filter'] = 'jurisdiction'
        context['active_indicator'] = indicator
        context['sort'] = sorting
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
        facet_fields = context.get('facets').get('fields')
        parent_cats = update_facet_data(self.request, facet_fields, 'parent_category', Category)
        all_cats = update_facet_data(self.request, facet_fields, 'category', Category)
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
        facet_fields = context.get('facets').get('fields')
        parent_cats = update_facet_data(self.request, facet_fields, 'parent_category', Category)
        all_cats = update_facet_data(self.request, facet_fields, 'category', Category)
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = Dataset.objects.all().first().created
        modified_cats = []
        chart_data = []

        top_cats = update_facet_data(self.request, facet_fields, 'category', Category)
        sorted_top_cats = sorted(top_cats, key=lambda cat: cat['count'], reverse=True)[:10]

        frequency, ff = get_frequency_and_format(duration)

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
        if sorting == 'sort-asc':
            modified_cats = sorted(modified_cats, key=lambda dd: dd['count'], reverse=False)
        if indicator != 'dataset-count':
            for single in modified_cats:
                if 'dataset_ids' in single:
                    if indicator == 'download-request-count' or indicator == 'download-object-count':
                        models = Model.objects.filter(dataset_id__in=single['dataset_ids']).values_list(
                            'metadata__name', flat=True)
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
            if sorting == 'sort-desc':
                modified_cats = sorted(modified_cats, key=lambda dd: dd['stats'], reverse=True)
            else:
                modified_cats = sorted(modified_cats, key=lambda dd: dd['stats'], reverse=False)

        if start_date:
            labels = pd.period_range(start=start_date,
                                     end=datetime.now(),
                                     freq=frequency).tolist()

        sort = 0
        for index, c in enumerate(sorted_top_cats):
            sort += 1
            cc = Category.objects.get(pk=c['filter_value'])
            cat_dataset_ids = Dataset.objects.filter(category=cc).values_list('pk', flat=True)
            total = 0
            temp = []
            for label in labels:
                if indicator == 'dataset-count':
                    total += Dataset.objects.filter(category=cc, created__year=label.year).count()
                else:
                    stat = DatasetStats.objects.filter(dataset_id__in=cat_dataset_ids, created__year=label.year)
                    per_datasets = 0
                    if len(stat) > 0:
                        for st in stat:
                            if indicator == 'request-count':
                                if st.request_count is not None:
                                    per_datasets += st.request_count
                            elif indicator == 'project-count':
                                if st.project_count is not None:
                                    per_datasets += st.project_count
                            elif indicator == 'distribution-count':
                                if st.distribution_count is not None:
                                    per_datasets += st.distribution_count
                            elif indicator == 'object-count':
                                if st.object_count is not None:
                                    per_datasets += st.object_count
                            elif indicator == 'field-count':
                                if st.field_count is not None:
                                    per_datasets += st.field_count
                            elif indicator == 'model-count':
                                if st.model_count is not None:
                                    per_datasets += st.model_count
                            elif indicator == 'level-average':
                                lev = []
                                if st.maturity_level is not None:
                                    lev.append(st.maturity_level)
                                level_avg = int(sum(lev) / len(lev))
                                per_datasets = level_avg

                    total = per_datasets
                if frequency == 'W':
                    temp.append({'x': _date(label.start_time, ff), 'y': total})
                else:
                    temp.append({'x': _date(label, ff), 'y': total})
            dt = {
                'label': c['display_value'],
                'data': temp,
                'borderWidth': 1,
                'fill': True,
                'sort': sort
            }
            chart_data.append(dt)

        chart_data = sorted(chart_data, key=lambda x: x['sort'])

        context['data'] = json.dumps(chart_data)
        context['graph_title'] = _('Rodiklis pagal rinkinio būseną laike')
        context['yAxis_title'] = Y_TITLES[indicator]
        context['xAxis_title'] = _('Laikas')
        context['categories'] = modified_cats
        context['max_count'] = max_count
        context['duration'] = duration
        context['active_filter'] = 'category'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        return context


class CategoryStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/categories.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        facet_fields = context.get('facets').get('fields')
        all_cats = update_facet_data(self.request, facet_fields, 'category', Category)
        child_titles = []
        cat_titles = []
        indicator = self.request.GET.get('indicator', None)
        sorting = self.request.GET.get('sort', None)
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
        if sorting == 'sort-asc':
            filtered_cats = sorted(filtered_cats, key=lambda dd: dd['count'], reverse=False)
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
            if sorting is None or sorting == 'sort-desc':
                filtered_cats = sorted(filtered_cats, key=lambda d: d['stats'], reverse=True)
            else:
                filtered_cats = sorted(filtered_cats, key=lambda d: d['stats'], reverse=False)
            # filtered_cats = sorted(filtered_cats, key=lambda d: d['stats'], reverse=True)
        context['max_count'] = max_count
        context['categories'] = filtered_cats
        context['current_object'] = self.kwargs.get('pk')
        context['active_filter'] = 'category'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        return context


class PublicationStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        duration = self.request.GET.get('duration', None) or 'duration-yearly'
        start_date = Dataset.objects.all().first().created
        year_stats = {}
        # quarter_stats = {}
        # monthly_stats = {}
        chart_data = []

        frequency, ff = get_frequency_and_format(duration)

        labels = []
        if start_date:
            labels = pd.period_range(
                start=start_date,
                end=datetime.now(),
                freq=frequency
            ).tolist()

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
                                level_avg = int(sum(lev) / len(lev))
                                year_stats[yr] = level_avg
                    else:
                        year_stats[yr] = 0
        for key, value in year_stats.items():
            if max_count < value:
                max_count = value
        keys = list(year_stats.keys())
        values = list(year_stats.values())
        sorted_value_index = np.argsort(values)
        if sorting == 'sort-year-desc':
            year_stats = OrderedDict(sorted(year_stats.items(), reverse=True))
        elif sorting == 'sort-year-asc':
            year_stats = OrderedDict(sorted(year_stats.items(), reverse=False))
        elif sorting == 'sort-desc':
            year_stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
        elif sorting == 'sort-asc':
            year_stats = {keys[i]: values[i] for i in sorted_value_index}

        sort = 0
        for index, y in enumerate(year_stats.keys()):
            sort += 1
            dataset_ids = Dataset.objects.filter(created__year=y).values_list('pk', flat=True)
            total = 0
            temp = []
            for label in labels:
                if indicator == 'dataset-count':
                    total += Dataset.objects.filter(pk__in=dataset_ids, created__year=label.year).count()
                else:
                    stat = DatasetStats.objects.filter(dataset_id__in=dataset_ids)
                    per_datasets = 0
                    if len(stat) > 0:
                        for st in stat:
                            if indicator == 'request-count':
                                if st.request_count is not None:
                                    per_datasets += st.request_count
                            elif indicator == 'project-count':
                                if st.project_count is not None:
                                    per_datasets += st.project_count
                            elif indicator == 'distribution-count':
                                if st.distribution_count is not None:
                                    per_datasets += st.distribution_count
                            elif indicator == 'object-count':
                                if st.object_count is not None:
                                    per_datasets += st.object_count
                            elif indicator == 'field-count':
                                if st.field_count is not None:
                                    per_datasets += st.field_count
                            elif indicator == 'model-count':
                                if st.model_count is not None:
                                    per_datasets += st.model_count
                            elif indicator == 'level-average':
                                lev = []
                                if st.maturity_level is not None:
                                    lev.append(st.maturity_level)
                                level_avg = int(sum(lev) / len(lev))
                                per_datasets = level_avg

                    total = per_datasets
                if frequency == 'W':
                    temp.append({'x': _date(label.start_time, ff), 'y': total})
                else:
                    temp.append({'x': _date(label, ff), 'y': total})
            dt = {
                'label': y,
                'data': temp,
                'borderWidth': 1,
                'fill': True,
                'sort': sort
            }
            chart_data.append(dt)

        chart_data = sorted(chart_data, key=lambda x: x['sort'])

        context['data'] = json.dumps(chart_data)
        context['graph_title'] = _('Rodiklis pagal rinkinio būseną laike')
        context['yAxis_title'] = Y_TITLES[indicator]
        context['xAxis_title'] = _('Laikas')
        context['year_stats'] = year_stats
        context['max_count'] = max_count
        context['duration'] = duration
        context['active_filter'] = 'publication'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        return context


class YearStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        year_stats = {}
        quarter_stats = {}
        selected_year = str(self.kwargs['year'])

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
                        models = Model.objects.filter(dataset_id__in=dataset_ids).values_list('metadata__name',
                                                                                              flat=True)
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
        keys = list(quarter_stats.keys())
        values = list(quarter_stats.values())
        sorted_value_index = np.argsort(values)
        if sorting == 'sort-year-desc':
            quarter_stats = OrderedDict(sorted(quarter_stats.items(), reverse=False))
        elif sorting == 'sort-year-asc':
            quarter_stats = OrderedDict(sorted(quarter_stats.items(), reverse=True))
        elif sorting == 'sort-asc':
            quarter_stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
        elif sorting == 'sort-desc':
            quarter_stats = {keys[i]: values[i] for i in sorted_value_index}
        context['selected_year'] = selected_year
        context['year_stats'] = quarter_stats
        context['max_count'] = max_count
        context['current_object'] = str('year/' + selected_year)
        context['active_filter'] = 'publication'
        context['active_indicator'] = indicator
        context['sort'] = sorting
        return context


class QuarterStatsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/publications.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        datasets = self.get_queryset()
        indicator = self.request.GET.get('indicator', None) or 'dataset-count'
        sorting = self.request.GET.get('sort', None) or 'sort-desc'
        # year_stats = {}
        # quarter_stats = {}
        monthly_stats = {}
        selected_quarter = str(self.kwargs['quarter'])

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
        keys = list(monthly_stats.keys())
        values = list(monthly_stats.values())
        sorted_value_index = np.argsort(values)
        if sorting == 'sort-year-desc':
            monthly_stats = OrderedDict(sorted(monthly_stats.items(), reverse=False))
        elif sorting == 'sort-year-asc':
            monthly_stats = OrderedDict(sorted(monthly_stats.items(), reverse=True))
        elif sorting == 'sort-asc':
            monthly_stats = {keys[i]: values[i] for i in np.flip(sorted_value_index)}
        elif sorting == 'sort-desc':
            monthly_stats = {keys[i]: values[i] for i in sorted_value_index}
        context['selected_quarter'] = self.kwargs['quarter']
        # context['year_stats'] = quarter_stats
        context['year_stats'] = monthly_stats
        context['max_count'] = max_count
        context['current_object'] = str('quarter/' + selected_quarter)
        context['active_filter'] = 'publication'
        context['active_indicator'] = indicator
        context['sort'] = sorting
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


class DatasetAttributionCreateView(PermissionRequiredMixin, CreateView):
    model = DatasetAttribution
    form_class = DatasetAttributionForm
    template_name = 'vitrina/datasets/attribution_form.html'

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('dataset_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.UPDATE,
            self.dataset
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dataset'] = self.dataset
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        return context

    def form_valid(self, form):
        self.object: DatasetAttribution = form.save(commit=False)
        self.object.dataset = self.dataset
        self.object.save()
        return redirect(self.dataset.get_absolute_url())


class DatasetAttributionDeleteView(PermissionRequiredMixin, DeleteView):
    model = DatasetAttribution

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('dataset_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.UPDATE,
            self.dataset
        )

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def get_success_url(self):
        return self.dataset.get_absolute_url()


class DatasetRelationCreateView(PermissionRequiredMixin, CreateView):
    model = DatasetRelation
    form_class = DatasetRelationForm
    template_name = 'vitrina/datasets/relation_form.html'

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(
            self.request.user,
            Action.UPDATE,
            self.dataset
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dataset'] = self.dataset
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        return context

    def form_valid(self, form):
        self.object: DatasetRelation = form.save(commit=False)

        if relation := form.cleaned_data.get('relation_type'):
            inverse = False
            if relation.endswith('_inv'):
                relation = relation.replace('_inv', '')
                inverse = True
            try:
                relation = Relation.objects.get(pk=int(relation))
            except (ValueError, ObjectDoesNotExist) as e:
                messages.error(self.request, e)
                return redirect(self.dataset.get_absolute_url())

            self.object.relation = relation
            if inverse:
                self.object.dataset = self.object.part_of
                self.object.part_of = self.dataset
            else:
                self.object.dataset = self.dataset
            self.object.save()
            self.object.dataset.part_of.add(self.object)

            # need to save to update search index
            self.object.dataset.save()
            self.object.part_of.save()

        return redirect(self.dataset.get_absolute_url())


class DatasetRelationDeleteView(PermissionRequiredMixin, DeleteView):
    model = DatasetRelation

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('dataset_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.dataset)

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)

    def get_success_url(self):
        return self.dataset.get_absolute_url()


class DatasetPlanView(
    HistoryMixin,
    DatasetStructureMixin,
    PlanMixin,
    TemplateView
):
    template_name = 'vitrina/datasets/plans.html'
    context_object_name = 'dataset'
    detail_url_name = 'dataset-detail'
    history_url_name = 'dataset-plans-history'
    plan_url_name = 'dataset-plans'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        context['plans'] = self.dataset.plandataset_set.all()
        context['can_manage_plans'] = has_perm(
            self.request.user,
            Action.PLAN,
            self.dataset
        )
        context['can_view_members'] = has_perm(
            self.request.user,
            Action.VIEW,
            Representative,
            self.dataset
        )
        return context

    def get_history_object(self):
        return self.dataset

    def get_detail_object(self):
        return self.dataset

    def get_plan_object(self):
        return self.dataset


class DatasetIncludePlanView(PermissionRequiredMixin, RevisionMixin, CreateView):
    form_class = DatasetPlanForm
    template_name = 'base_form.html'

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.PLAN, self.dataset)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dataset'] = self.dataset
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Duomenų rinkinio įtraukimas į planą")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.dataset = self.dataset
        self.object.save()

        self.object.plan.save()
        set_comment(_(f'Į planą "{self.object.plan}" įtrauktas duomenų rinkinys "{self.dataset}".'))
        return redirect(reverse('dataset-plans', args=[self.dataset.pk]))


class DatasetCreatePlanView(PermissionRequiredMixin, RevisionMixin, CreateView):
    model = Plan
    form_class = PlanForm
    template_name = 'vitrina/plans/form.html'

    dataset: Dataset

    def dispatch(self, request, *args, **kwargs):
        self.dataset = get_object_or_404(Dataset, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.PLAN, self.dataset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _("Naujas planas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[self.dataset.pk]): self.dataset.title,
        }
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['obj'] = self.dataset
        kwargs['user'] = self.request.user
        kwargs['organizations'] = [self.dataset.organization]
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        PlanDataset.objects.create(
            plan=self.object,
            dataset=self.dataset
        )
        set_comment(_(f'Pridėtas planas "{self.object}". Į planą įtrauktas duomenų rinkinys "{self.dataset}".'))
        return redirect(reverse('dataset-plans', args=[self.dataset.pk]))


class DatasetDeletePlanView(PermissionRequiredMixin, RevisionMixin, DeleteView):
    model = PlanDataset
    template_name = 'confirm_delete.html'

    def has_permission(self):
        dataset = self.get_object().dataset
        return has_perm(self.request.user, Action.PLAN, dataset)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        plan = self.object.plan
        dataset = self.object.dataset
        self.object.delete()

        plan.save()
        set_comment(_(f'Iš plano "{plan}" pašalintas duomenų rinkinys "{dataset}".'))
        return redirect(reverse('dataset-plans', args=[dataset.pk]))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = self.get_object().dataset
        context['current_title'] = _("Plano pašalinimas")
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('dataset-list'): _('Duomenų rinkiniai'),
            reverse('dataset-detail', args=[dataset.pk]): dataset.title,
        }
        return context


class DatasetDeletePlanDetailView(DatasetDeletePlanView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object().plan.receiver
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('organization-list'): _('Organizacijos'),
            reverse('organization-detail', args=[organization.pk]): organization.title,
        }
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        plan = self.object.plan
        dataset = self.object.dataset
        self.object.delete()

        plan.save()
        set_comment(_(f'Iš plano "{plan}" pašalintas duomenų rinkinys "{dataset}".'))
        return redirect(reverse('plan-detail', args=[plan.receiver.pk, plan.pk]))


class DatasetPlansHistoryView(DatasetStructureMixin, PlanMixin, HistoryView):
    model = Dataset
    detail_url_name = "dataset-detail"
    history_url_name = "dataset-plans-history"
    plan_url_name = 'dataset-plans'
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

    def get_history_objects(self):
        dataset_plan_ids = PlanDataset.objects.filter(dataset=self.object).values_list('plan_id', flat=True)
        return Version.objects.get_for_model(Plan).filter(
            object_id__in=list(dataset_plan_ids)
        ).order_by('-revision__date_created')
