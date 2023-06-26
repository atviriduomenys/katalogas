import csv
import datetime
import itertools
import json
import secrets

import pandas as pd

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
from django.views.generic import TemplateView, DetailView, ListView
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
from vitrina.views import HistoryView, HistoryMixin
from vitrina.datasets.forms import DatasetStructureImportForm, DatasetForm, DatasetSearchForm, AddProjectForm, \
    DatasetAttributionForm
from vitrina.datasets.forms import DatasetMemberUpdateForm, DatasetMemberCreateForm
from vitrina.datasets.services import update_facet_data, get_projects
from vitrina.datasets.models import Dataset, DatasetStructure, DatasetGroup, DatasetAttribution
from vitrina.datasets.structure import detect_read_errors, read
from vitrina.classifiers.models import Category, Frequency
from vitrina.helpers import get_selected_value
from vitrina.orgs.helpers import is_org_dataset_list
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.resources.models import DatasetDistribution
from vitrina.users.models import User
from vitrina.helpers import get_current_domain
from django.utils.timezone import now, make_aware
from pandas import period_range


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
        }
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
        return context


class DatasetDetailView(LanguageChoiceMixin, HistoryMixin, DetailView):
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
            'attributions': dataset.datasetattribution_set.order_by('attribution'),
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
        groups = form.cleaned_data['groups']
        self.object.groups.set(groups)
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
        groups = form.cleaned_data['groups']
        tags = form.cleaned_data['tags']
        self.object.groups.set(groups)
        self.object.tags.set(tags)
        self.object.save()
        set_comment(Dataset.EDITED)
        return HttpResponseRedirect(self.get_success_url())


class DatasetHistoryView(HistoryView):
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
        return HttpResponseRedirect(self.get_success_url())


class DatasetMembersView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    HistoryMixin,
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


class DatasetProjectsView(HistoryMixin, ListView):
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
    template_name = 'vitrina/datasets/statistics_graph.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        datasets = self.get_queryset()
        data = []
        status_translations = Comment.get_statuses()

        inventored_styles = {'borderColor': 'black',
                             'backgroundColor': 'rgba(255, 179, 186, 0.9)',
                             'fill': True,
                             'sort': 1}
        structured_styles = {'borderColor': 'black',
                             'backgroundColor': 'rgba(186,225,255, 0.9)',
                             'fill': True,
                             'sort': 2}
        opened_styles = {'borderColor': 'black',
                         'backgroundColor': 'rgba(255, 223, 186, 0.9)',
                         'fill': True,
                         'sort': 3}

        most_recent_comments = Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id__in=datasets.values_list('pk', flat=True),
            status__isnull=False).values('object_id')\
            .annotate(latest_status_change=Max('created')).values('object_id', 'latest_status_change')\
            .order_by('latest_status_change')

        dataset_status = Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(Dataset),
            object_id__in=most_recent_comments.values('object_id'),
            created__in=most_recent_comments.values('latest_status_change'))\
            .annotate(year=ExtractYear('created'), month=ExtractMonth('created'))\
            .values('object_id', 'status', 'year', 'month')

        start_date = most_recent_comments.first().get('latest_status_change') if most_recent_comments else None
        statuses = dataset_status.order_by('status').values_list('status', flat=True).distinct()

        if start_date:
            labels = pd.period_range(start=start_date,
                                     end=datetime.date.today(),
                                     freq='M').tolist()

            for item in statuses:
                total = 0
                temp = []
                for label in labels:
                    total += dataset_status.filter(status=item, year=label.year, month=label.month)\
                        .values('object_id')\
                        .annotate(count=Count('object_id', distinct=True))\
                        .count()
                    temp.append({'x': _date(label, 'y b'), 'y': total})
                dict = {'label': str(status_translations[item]),
                        'data': temp,
                        'borderWidth': 1}

                if item == 'INVENTORED':
                    dict.update(inventored_styles)
                elif item == 'STRUCTURED':
                    dict.update(structured_styles)
                elif item == 'OPENED':
                    dict.update(opened_styles)

                data.append(dict)
        data = sorted(data, key=lambda x: x['sort'])
        context['data'] = json.dumps(data)
        context['graph_title'] = _('Duomenų rinkinių kiekis laike')
        context['dataset_count'] = len(datasets)
        context['yAxis_title'] = _('Duomenų rinkiniai')
        context['xAxis_title'] = _('Laikas')
        context['stats'] = 'status'
        return context


class DatasetManagementsView(DatasetListView):
    facet_fields = DatasetListView.facet_fields
    template_name = 'vitrina/datasets/jurisdictions.html'
    paginate_by = 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        max_count = 0
        context['jurisdictions'] = context['jurisdiction_facet']
        for org in context['jurisdictions']:
            if max_count < org.get('count'):
                max_count = org.get('count')
        context['max_count'] = max_count
        context['stats'] = 'jurisdiction'
        return context


class DatasetsStatsView(DatasetListView):
    template_name = 'graphs/datasets_yearly_change_graph.html'
    facet_fields = DatasetListView.facet_fields
    paginate_by = 0

    def get_date_labels(self):
        oldest_dataset_date = Dataset.objects.order_by('created').first().created
        return period_range(start=oldest_dataset_date, end=now(), freq='Y').astype(str).tolist()

    def get_categories(self):
        return [
            {'title': cat.title, 'id': cat.id} for cat in Category.objects.filter(featured=True).order_by('title')
        ]

    def get_color(self, year):
        color_map = {
            '2019': '#03256C',
            '2020': '#2541B2',
            '2021': '#1768AC',
            "2022": '#06BEE1',
            "2023": "#4193A2",
            # FIXME: this should net be hardcoded, use colormaps:
            #        https://matplotlib.org/stable/tutorials/colors/colormaps.html
            #        (maybe `winter`?)
        }
        return color_map.get(year)

    def get_statistics_data(self):
        categories = self.get_categories()
        query_set = self.get_queryset()
        data = {
            'labels': [cat.get('title') for cat in categories] 
        }
        datasets = []
        date_labels = self.get_date_labels()
        for date_label in date_labels:
            dataset_counts = []
            for category in categories:
                filtered_ids = query_set.filter(category__id=category.get('id')).values_list('pk', flat=True)
                created_date = datetime.datetime(int(date_label), 1, 1)
                created_date = make_aware(created_date)
                dataset_counts.append(
                    Dataset.objects.filter(id__in=filtered_ids, created__lt=created_date).count()
                )
            datasets.append(
                {
                    'label': date_label,
                    'data': dataset_counts,
                    'backgroundColor': self.get_color(date_label)

                }
            )
        data['datasets'] = datasets
        return data, query_set

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data, qs = self.get_statistics_data()
        context['data'] = data
        context['dataset_count'] = len(qs)
        context['graph_title'] = 'Duomenų rinkinių atvėrimo progresas'
        return context


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        return context

    def form_valid(self, form):
        self.object: DatasetAttribution = form.save(commit=False)
        self.object.dataset = self.dataset
        self.object.save()
        return redirect(self.dataset.get_absolute_url())
