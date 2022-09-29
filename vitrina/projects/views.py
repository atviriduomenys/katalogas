from django.views.generic import ListView, DetailView, CreateView, UpdateView

from vitrina.projects.forms import ProjectForm
from vitrina.projects.models import Project

from django.utils.translation import gettext_lazy as _


class ProjectListView(ListView):
    model = Project
    queryset = Project.public.order_by('-created')
    template_name = 'vitrina/projects/list.html'
    paginate_by = 20


class ProjectDetailView(DetailView):
    model = Project
    template_name = 'vitrina/projects/detail.html'


class ProjectCreateView(CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Panaudos atvejo registracija')
        return context_data


class ProjectUpdateView(UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Panaudot atvejo redagavimas')
        return context_data
