from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.views.generic import ListView, CreateView, UpdateView
from reversion import set_comment
from reversion.views import RevisionMixin

from vitrina.projects.forms import ProjectForm
from vitrina.projects.models import Project

from django.utils.translation import gettext_lazy as _

from vitrina.views import HistoryDetailView, HistoryView


class ProjectListView(ListView):
    model = Project
    queryset = Project.public.order_by('-created')
    template_name = 'vitrina/projects/list.html'
    paginate_by = 20


class ProjectDetailView(HistoryDetailView):
    model = Project
    template_name = 'vitrina/projects/detail.html'
    detail_url_name = 'project-detail'
    history_url_name = 'project-history'


class ProjectCreateView(RevisionMixin, LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        set_comment(Project.CREATED)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['current_title'] = _('Panaudos atvejo registracija')
        return context_data


class ProjectUpdateView(RevisionMixin, LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'base_form.html'

    def form_valid(self, form):
        super().form_valid(form)
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
