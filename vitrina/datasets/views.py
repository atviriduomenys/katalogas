import csv
import itertools

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import FileResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


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

from vitrina.projects.models import Project
from vitrina.views import HistoryView, HistoryMixin
from vitrina.datasets.forms import DatasetStructureImportForm, DatasetForm, DatasetSearchForm, AddProjectForm
from vitrina.datasets.forms import DatasetMemberUpdateForm, DatasetMemberCreateForm
from vitrina.datasets.services import update_facet_data
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.datasets.structure import detect_read_errors, read
from vitrina.classifiers.models import Category, Frequency
from vitrina.helpers import get_selected_value
from vitrina.orgs.helpers import is_org_dataset_list
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action
from vitrina.resources.models import DatasetDistribution
from vitrina.users.models import User
from vitrina.helpers import get_current_domain


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


class DatasetDetailView(LanguageChoiceMixin, HistoryMixin, DetailView):
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
    TranslatableCreateView,
    LanguageChoiceMixin
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
    TranslatableUpdateView,
    ViewUrlMixin
):
    model = Dataset
    template_name = 'base_form.html'
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
        return HttpResponseRedirect(self.get_success_url())


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
        return (
            Project.public.
            filter(datasets=self.object).
            order_by('-created')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.object
        context['can_add_projects'] = has_perm(
            self.request.user,
            Action.ADD_PROJECT,
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
                Project.public.
                filter(user=self.request.user).
                exists()
            )
        else:
            context['has_projects'] = False
        print(context)
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
        return has_perm(self.request.user, Action.ADD_PROJECT, self.dataset)

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
        return has_perm(self.request.user, Action.DELETE, self.project)

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse('dataset-projects', kwargs={'pk': self.dataset.pk}))

    def delete(self, request, *args, **kwargs):
        self.project.datasets.remove(self.dataset.pk)
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        return reverse('dataset-projects', kwargs={'pk': self.dataset.pk})
