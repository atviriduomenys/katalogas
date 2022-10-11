from typing import Optional

from django.db.models import Q
from django.db.models import QuerySet

from vitrina.tasks.models import Task
from vitrina.users.models import User


def get_active_tasks(
    user: User,
    queryset: Optional[QuerySet] = None,
) -> QuerySet:
    queryset = queryset or Task.objects.all()
    return queryset.filter(
        Q(user=user) |
        (Q(role__isnull=False) & Q(role=user.role)) |
        (Q(organization__isnull=False) & Q(organization=user.organization))
    )
