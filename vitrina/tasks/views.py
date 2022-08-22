from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from vitrina.tasks.models import Task
from vitrina.users.models import User


class TaskListView(ListView):
    model = Task
    template_name = 'vitrina/tasks/list.html'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user_pk = self.kwargs.get('pk', None)
        if user_pk:
            user = get_object_or_404(User, pk=user_pk)
            queryset = queryset.filter(Q(user=user) | (Q(role__isnull=False) & Q(role=user.role)) |
                                       (Q(organization__isnull=False) & Q(organization=user.organization)))
        return queryset
