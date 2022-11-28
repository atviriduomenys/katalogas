from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.views.generic.edit import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponseRedirect
from django.urls import reverse

from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.datasets.models import Dataset
from vitrina.orgs.services import has_perm, Action
from vitrina.projects.forms import ProjectForm, AddDatasetForm
from vitrina.projects.models import Project

from vitrina.views import HistoryMixin, HistoryView


class ProjectListView(ListView):
    model = Project
    queryset = Project.public.order_by('-created')
    template_name = 'vitrina/projects/list.html'
    paginate_by = 20


class ProjectDetailView(HistoryMixin, DetailView):
    model = Project
    template_name = 'vitrina/projects/detail.html'
    detail_url_name = 'project-detail'
    history_url_name = 'project-history'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_update_project'] = has_perm(
            self.request.user,
            Action.UPDATE,
            self.object
        )
        return context


class ProjectCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    CreateView
):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, Project)

    def form_valid(self, form):
        self.object = form.save(commit=True)
        self.object.user = self.request.user
        self.object.status = Project.CREATED
        self.object.datasets.set(form.cleaned_data['dataset'])
        self.object.save()
        set_comment(Project.CREATED)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Panaudos atvejo registracija')
        return context_data


class ProjectUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def has_permission(self):
        project = self.get_object()
        return has_perm(self.request.user, Action.UPDATE, project)

    def form_valid(self, form):
        super().form_valid(form)
        self.object = form.save(commit=True)
        for dataset in form.cleaned_data['dataset']:
            self.object.datasets.add(dataset.id)
        self.object.save()
        set_comment(Project.EDITED)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Panaudos atvejo redagavimas')
        return context_data


class ProjectHistoryView(HistoryView):
    model = Project
    detail_url_name = 'project-detail'
    history_url_name = 'project-history'
    tabs_template_name = 'vitrina/projects/tabs.html'


class ProjectDatasetsView(HistoryMixin, ListView):
    model = Dataset
    template_name = 'vitrina/projects/datasets.html'
    paginate_by = 20

    object: Dataset
    detail_url_name = 'project-detail'
    history_url_name = 'project-history'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Project, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.object.datasets.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object
        context['can_update_project'] = has_perm(
            self.request.user,
            Action.UPDATE,
            self.object
        )
        return context


class ProjectAddDatasetView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RevisionMixin,
    UpdateView
):
    model = Project
    form_class = AddDatasetForm
    template_name = 'base_form.html'

    def has_permission(self):
        project = self.get_object()
        return has_perm(self.request.user, Action.UPDATE, project)

    def form_valid(self, form):
        super().form_valid(form)
        self.object = form.save(commit=False)
        print(self.object)
        for dataset in form.cleaned_data['dataset']:
            self.object.datasets.add(dataset)
        self.object.save()
        return HttpResponseRedirect(reverse('project-datasets', kwargs={'pk': self.object.pk}))

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Duomenų rinkinių pridėjimas')
        return context_data


class RemoveDatasetView(LoginRequiredMixin, PermissionRequiredMixin, View):
    def has_permission(self):
        project = get_object_or_404(Project, pk=self.kwargs.get('project_id'))
        return has_perm(self.request.user, Action.UPDATE, project)

    def get(self, request, project_id, dataset_id):
        project = get_object_or_404(Project, pk=project_id)
        project.datasets.remove(dataset_id)
        return HttpResponseRedirect(reverse('project-datasets', kwargs={'pk': project_id}))
