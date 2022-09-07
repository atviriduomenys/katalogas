from django.views.generic import ListView, DetailView

from vitrina.projects.models import Project


class ProjectListView(ListView):
    model = Project
    queryset = Project.public.order_by('-created')
    template_name = 'vitrina/projects/list.html'
    paginate_by = 20


class ProjectDetailView(DetailView):
    model = Project
    template_name = 'vitrina/projects/detail.html'
