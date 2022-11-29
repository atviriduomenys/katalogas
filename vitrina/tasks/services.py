from datetime import timedelta
from typing import Optional

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Min, Max
from django.db.models import QuerySet
from django.utils import timezone

from vitrina.helpers import get_non_working_days, add_work_days
from vitrina.orgs.models import Organization
from vitrina.orgs.services import is_supervisor
from vitrina.settings import VITRINA_TASK_RAISE_2, VITRINA_TASK_RAISE_1
from vitrina.tasks.models import Task
from vitrina.users.models import User


def get_active_tasks(
    user: User,
    queryset: Optional[QuerySet] = None,
) -> QuerySet:
    queryset = queryset or Task.objects.all()

    date_from = queryset.values('created').aggregate(Min('created'))['created__min']
    date_to = queryset.values('created').aggregate(Max('created'))['created__max']
    if date_from:
        date_from = date_from.date()
    if date_to:
        # adding VITRINA_TASK_RAISE_2 and 10 more, just to be safe
        date_to = (date_to + timedelta(days=(VITRINA_TASK_RAISE_2 + 10))).date()
    non_working_days = get_non_working_days(
        include_weekends=True,
        date_from=date_from,
        date_to=date_to,
    )

    user_organization_ids = user.representative_set.filter(
        content_type=ContentType.objects.get_for_model(Organization),
        object_id__isnull=False
    ).values_list('object_id', flat=True)
    user_task_ids = list(queryset.filter(
        Q(user=user) |
        Q(organization__pk__in=user_organization_ids)
    ).values_list('pk', flat=True))

    # add tasks that should be shown to supervisor and admin
    for task in queryset:
        if task.status != Task.COMPLETED:
            if task.organization and \
                    is_supervisor(user, task.organization) and \
                    add_work_days(task.created, VITRINA_TASK_RAISE_1, non_working_days) <= timezone.now():
                user_task_ids.append(task.pk)
            elif (user.is_staff or user.is_superuser) and \
                    add_work_days(task.created, VITRINA_TASK_RAISE_2, non_working_days) <= timezone.now():
                user_task_ids.append(task.pk)
    return queryset.filter(pk__in=user_task_ids)


