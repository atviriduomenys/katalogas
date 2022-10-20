from django.http import HttpResponseRedirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils.translation import gettext_lazy as _

from vitrina.orgs.services import has_perm, Action
from vitrina.projects.forms import ProjectForm
from vitrina.projects.models import Project


class ProjectListView(ListView):
    model = Project
    queryset = Project.public.order_by('-created')
    template_name = 'vitrina/projects/list.html'
    paginate_by = 20


class ProjectDetailView(DetailView):
    model = Project
    template_name = 'vitrina/projects/detail.html'

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
    CreateView
):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def has_permission(self):
        return has_perm(self.request.user, Action.CREATE, Project)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Panaudos atvejo registracija')
        return context_data

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.status = Project.CREATED
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class ProjectUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def has_permission(self):
        project = self.get_object()
        return has_perm(self.request.user, Action.UPDATE, project)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Panaudot atvejo redagavimas')
        return context_data
