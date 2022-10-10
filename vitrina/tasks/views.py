from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from vitrina.tasks.models import Task
from vitrina.tasks.services import get_active_tasks


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'vitrina/tasks/list.html'
    paginate_by = 20

    def get_queryset(self):
        queryset = get_active_tasks(self.request.user, super().get_queryset())
        return queryset.order_by('-created')
