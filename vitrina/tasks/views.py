from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView, DeleteView

from vitrina.orgs.services import Action, has_perm
from vitrina.tasks.models import Task
from vitrina.tasks.services import get_active_tasks


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'vitrina/tasks/list.html'
    paginate_by = 20

    def get_queryset(self):
        queryset = get_active_tasks(self.request.user, super().get_queryset())
        return queryset.order_by('-created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tasks = self.get_queryset()
        cats = [
            {'title': 'Vykdytojas', 'types':
                [
                    {'subtype': 'Mano užduotys', 'count': tasks.filter(user_id=self.request.user.pk).count()},
                    {'subtype': 'Visos užduotys', 'count': len(tasks)}
                ]
             },
            {'title': 'Būsena', 'types':
                [
                    {'subtype': 'Registruota', 'count': tasks.filter(status='created').count()},
                    {'subtype': 'Priskirta', 'count': tasks.filter(status='assigned').count()},
                    {'subtype': 'Išspręsta', 'count': tasks.filter(status='completed').count()}
                ]
             },
            {'title': 'Tipas', 'types':
                [
                    {'subtype': 'Komentaras', 'count': tasks.filter(type='comment').count()},
                    {'subtype': 'Prašymas', 'count': tasks.filter(type='request').count()},
                    {'subtype': 'Klaida', 'count': tasks.filter(type='error').count()},
                ]
             }
        ]
        context['cats'] = cats
        return context


class TaskView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'vitrina/tasks/detail.html'
    pk_url_kwarg = 'task_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.object
        if task.content_type is not None:
            print(task.content_type)
        org = 'Organizacijos pavadinimas'
        context['org'] = org
        return context


class CloseTaskView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = 'confirm_close.html'

    def dispatch(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=self.kwargs.get('task_id'))
        return super().dispatch(request, *args, **kwargs)

    def has_permission(self):
        return has_perm(self.request.user, Action.UPDATE, self.request_object)

    def delete(self, request, *args, **kwargs):
        self.task.status = Task.COMPLETED
        self.task.save()
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self):
        return reverse('user-task-list', kwargs={'pk': self.request.user.pk})
