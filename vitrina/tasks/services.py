from typing import Optional

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models import QuerySet

from vitrina.tasks.models import Task
from vitrina.users.models import User


def get_active_tasks(
    user: User,
    queryset: Optional[QuerySet] = None,
) -> QuerySet:
    queryset = queryset or Task.objects.all()
    roles = user.representative_set.values_list('role', flat=True).distinct()
    return queryset.filter(
        Q(user=user) |
        (Q(role__isnull=False) & Q(role__in=roles)) |
        (Q(organization__isnull=False) & Q(organization=user.organization))
    )
