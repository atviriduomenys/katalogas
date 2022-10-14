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
    if user.organization:
        content_type = ContentType.objects.get_for_model(user.organization)
        if user.representative_set.filter(object_id=user.organization.pk, content_type=content_type).exists():
            rep = user.representative_set.filter(object_id=user.organization.pk, content_type=content_type).first()
            return queryset.filter(
                Q(user=user) |
                (Q(role__isnull=False) & Q(role=rep.role)) |
                (Q(organization__isnull=False) & Q(organization=user.organization))
            )
    return queryset.filter(
        Q(user=user) |
        (Q(organization__isnull=False) & Q(organization=user.organization))
    )
