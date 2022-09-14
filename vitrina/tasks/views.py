from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from vitrina.tasks.models import Task


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'vitrina/tasks/list.html'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(Q(user=self.request.user) |
                                   (Q(role__isnull=False) & Q(role=self.request.user.role)) |
                                   (Q(organization__isnull=False) & Q(organization=self.request.user.organization)))
        return queryset.order_by('-created')
