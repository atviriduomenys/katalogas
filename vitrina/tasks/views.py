import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, DeleteView, TemplateView
from django.utils.translation import gettext_lazy as _
from haystack.generic_views import FacetedSearchView

from vitrina.helpers import Filter, get_filter_url
from vitrina.orgs.models import Organization
from vitrina.tasks.forms import TaskSearchForm
from vitrina.tasks.models import Task
from vitrina.tasks.services import get_active_tasks


class TaskListView(LoginRequiredMixin, FacetedSearchView):
    template_name = 'vitrina/tasks/list.html'
    paginate_by = 20

    facet_fields = [
        'status',
        'type',
        'user',
    ]
    form_class = TaskSearchForm
    max_num_facets = 20

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        queryset = super().get_queryset()
        active_tasks = get_active_tasks(self.request.user, all_tasks=True).values_list('pk', flat=True)
        queryset = queryset.filter(id__in=active_tasks)

        owner = self.request.GET.get('owner', 'all')
        if owner == 'user':
            queryset = queryset.filter(user__pk=self.request.user.pk)

        return queryset.order_by('due_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
        }

        facet_fields = context.get('facets').get('fields')
        form = context.get('form')
        filter_args = (self.request, form, facet_fields)
        context['filters'] = [
            Filter(
                *filter_args,
                'status',
                _("Būsena"),
                choices=Task.FILTER_STATUSES,
                multiple=False,
                is_int=False
            ),
            Filter(
                *filter_args,
                'type',
                _("Tipas"),
                choices=Task.FILTER_TYPES,
                multiple=False,
                is_int=False
            ),
        ]

        owner_selected_value = self.request.GET.get('owner', 'all')
        queryset = self.get_queryset()
        context['owner_filter'] = {
            'title': _("Vykdytojas"),
            'items': [
                {
                    'title': _('Mano užduotys'),
                    'url': get_filter_url(
                        self.request,
                        "owner",
                        "user",
                        owner_selected_value == "user",
                        facet_field=False
                    ),
                    "count": queryset.filter(user__pk=self.request.user.pk).count(),
                    "selected": owner_selected_value == "user"
                },
                {
                    'title': _('Visos užduotys'),
                    'url': get_filter_url(
                        self.request,
                        "owner",
                        "all",
                        owner_selected_value == "all",
                        facet_field=False
                    ),
                    "count": queryset.count(),
                    "selected": owner_selected_value == "all"
                }
            ]
        }
        context['search_url'] = reverse('user-task-list', args=[self.request.user.pk])
        context['search_query'] = dict(self.request.GET.copy())
        context['q'] = form.cleaned_data.get('q', '')
        return context


class TaskView(PermissionRequiredMixin, DetailView):
    model = Task
    template_name = 'vitrina/tasks/detail.html'
    pk_url_kwarg = 'task_id'

    task: Task

    def dispatch(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=kwargs.get('task_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if self.request.user and self.request.user.is_authenticated:
            user_tasks = get_active_tasks(self.request.user, all_tasks=True)
            if user_tasks.filter(pk=self.task.pk):
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        org = ''
        object_url = None
        if task.organization_id is not None:
            org = Organization.objects.filter(pk=task.organization_id).values_list('title', flat=True).first()
        if task.content_object:
            object_url = task.content_object.get_absolute_url
        context['org'] = org
        context['object_url'] = object_url
        context['parent_links'] = {
            reverse('home'): _('Pradžia'),
            reverse('user-task-list', args=[self.request.user.pk]): _('Užduotys'),
        }
        context['has_perm'] = self.has_permission()
        return context


class CloseTaskView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Task
    template_name = 'confirm_close.html'
    pk_url_kwarg = 'task_id'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Task, pk=self.kwargs.get('task_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if self.request.user and self.request.user.is_authenticated:
            user_tasks = get_active_tasks(self.request.user, all_tasks=True)
            if user_tasks.filter(pk=self.object.pk) and self.object.status != Task.COMPLETED:
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_title'] = _('Užduoties uždarymas')
        return context

    def delete(self, request, *args, **kwargs):
        self.object.status = Task.COMPLETED
        self.object.completed = datetime.datetime.now()
        self.object.save()
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        return reverse('user-task-list', kwargs={'pk': self.request.user.pk})


class AssignTaskView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'confirm_reassign.html'
    pk_url_kwarg = 'task_id'

    def dispatch(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=self.kwargs.get('task_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        if self.request.user and self.request.user.is_authenticated:
            user_tasks = get_active_tasks(self.request.user, all_tasks=True)
            if user_tasks.filter(pk=self.task.pk) and self.task.status != Task.COMPLETED:
                return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task'] = self.task
        return context

    def post(self, request, *args, **kwargs):
        if self.task is not None:
            self.task.user = self.request.user
            self.task.status = Task.ASSIGNED
            self.task.assigned = datetime.datetime.now()
            self.task.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('user-task-list', kwargs={'pk': self.request.user.pk})
