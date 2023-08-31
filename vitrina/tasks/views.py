import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, DeleteView, UpdateView, TemplateView

from vitrina.orgs.models import Organization
from vitrina.orgs.services import Action, has_perm
from vitrina.tasks.models import Task
from vitrina.tasks.services import get_active_tasks


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'vitrina/tasks/list.html'
    paginate_by = 20

    def get_queryset(self):
        queryset = Task.objects.filter(status__in=[Task.CREATED, Task.ASSIGNED])
        task_filter = self.request.GET.get('filter')
        if task_filter is None:
            queryset = queryset
        else:
            if task_filter == 'user':
                queryset = get_active_tasks(self.request.user, super().get_queryset())
            elif task_filter == 'all':
                queryset = queryset
            elif task_filter == Task.CREATED.lower():
                queryset = Task.objects.filter(status=Task.CREATED)
            elif task_filter == Task.ASSIGNED.lower():
                queryset = Task.objects.filter(status=Task.ASSIGNED)
            elif task_filter == Task.COMPLETED.lower():
                queryset = Task.objects.filter(status=Task.COMPLETED)
            elif task_filter == Task.COMMENT.lower():
                queryset = Task.objects.filter(type=Task.COMMENT)
            elif task_filter == Task.REQUEST.lower():
                queryset = Task.objects.filter(type=Task.REQUEST)
            else:
                queryset = Task.objects.filter(type__in=[Task.ERROR, Task.ERROR_FREQUENCY, Task.ERROR_DISTRIBUTION])

        return queryset.order_by('due_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_tasks = Task.objects.all()
        all_active_tasks = all_tasks.filter(status__in=[Task.CREATED, Task.ASSIGNED])
        active_user_tasks = get_active_tasks(self.request.user)
        closed_tasks = all_tasks.filter(status=Task.COMPLETED)
        cats = [
            {'title': 'Vykdytojas', 'types':
                [
                    {'subtype': 'Mano užduotys', 'count': active_user_tasks.count(), 'filter': 'user'},
                    {'subtype': 'Visos užduotys', 'count': all_active_tasks.count(), 'filter': 'all'}
                ]
             },
            {'title': 'Būsena', 'types':
                [
                    {'subtype': 'Registruota', 'count': all_tasks.filter(status=Task.CREATED).count(),
                     'filter': Task.CREATED.lower()},
                    {'subtype': 'Priskirta', 'count': all_tasks.filter(status=Task.ASSIGNED).count(),
                     'filter': Task.ASSIGNED.lower()},
                    {'subtype': 'Išspręsta', 'count': closed_tasks.count(),
                     'filter': Task.COMPLETED.lower()}
                ]
             },
            {'title': 'Tipas', 'types':
                [
                    {'subtype': 'Komentaras', 'count': all_tasks.filter(type=Task.COMMENT).count(),
                     'filter': Task.COMMENT.lower()},
                    {'subtype': 'Prašymas', 'count': all_tasks.filter(type=Task.REQUEST).count(),
                     'filter': Task.REQUEST.lower()},
                    {'subtype': 'Klaida', 'count': all_tasks.filter(type__in=[Task.ERROR, Task.ERROR_DISTRIBUTION,
                                                                              Task.ERROR_FREQUENCY]).count(),
                     'filter': Task.ERROR.lower()},
                ]
             }
        ]
        active_filter = self.request.GET.get('filter')
        if active_filter is None:
            active_filter = 'all'
        context['cats'] = cats
        context['active_filter'] = active_filter
        return context


class TaskView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'vitrina/tasks/detail.html'
    pk_url_kwarg = 'task_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        org = ''
        if task.organization_id is not None:
            org = Organization.objects.filter(pk=task.organization_id).values_list('title', flat=True).first()
        if task.object_id is not None and task.content_type_id is not None:
            object_url = task.content_object.get_absolute_url
        context['org'] = org
        context['object_url'] = object_url
        return context


class CloseTaskView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Task
    template_name = 'confirm_close.html'
    pk_url_kwarg = 'task_id'

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(Task, pk=self.kwargs.get('task_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.object)

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse('user-task-list', kwargs={'pk': self.request.user.pk}))

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
        return has_perm(self.request.user, Action.UPDATE, self.task)

    def handle_no_permission(self):
        return HttpResponseRedirect(reverse('user-task-list', kwargs={'pk': self.request.user.pk}))

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
