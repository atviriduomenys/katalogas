import datetime
import functools
import operator
from datetime import timedelta
from typing import Optional

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models import QuerySet
from django.utils import timezone

from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.settings import VITRINA_TASK_RAISE_2, VITRINA_TASK_RAISE_1
from vitrina.tasks.models import Task, Holiday
from vitrina.users.models import User


def get_past_work_date(
    days: int,
    exclude: list[datetime.date],  # weekends are excluded automatically
    *,
    now: datetime.date = None,
) -> datetime.date:
    now = now or timezone.now().date()
    res = now

    # Exclude weekends
    while days:
        res -= timedelta(days=1)
        if res.weekday() < 5:
            days -= 1

    # Exclude holidays
    for date in exclude:
        if (now <= date <= res) and date.weekday() < 5:
            res -= timedelta(days=1)

    return res


def get_holidays(
    date_from: datetime.date,
    date_to: datetime.date
):
    return Holiday.objects.filter(
        date__range=[date_from, date_to]
    ).values_list('date', flat=True)


def get_active_tasks(
    user: User,
    queryset: Optional[QuerySet] = None,
    now: datetime.date = None
) -> QuerySet:
    queryset = queryset or Task.objects.all()
    now = now or timezone.now().date()
    holidays = get_holidays(
        date_from=(now - timedelta(days=(VITRINA_TASK_RAISE_2 + 30))),
        date_to=now
    )
    date_1 = get_past_work_date(
        days=VITRINA_TASK_RAISE_1,
        exclude=holidays,
        now=now
    )
    date_2 = get_past_work_date(
        days=VITRINA_TASK_RAISE_2,
        exclude=holidays,
        now=now
    )

    orgs = user.representative_set.filter(
        object_id__isnull=False,
    )

    args = [
        # 1. User can see his own tasks.
        Q(user=user),
    ]

    for org in orgs:
        if isinstance(org.content_object, Organization):
            org = org.content_object
        elif isinstance(org.content_object, Dataset):
            org = org.content_object.organization
        args += [
            # 2. User can see his represented org tasks.
            Q(organization=org) |

            # 3. User can see his supervised orgs tasks.
            (
                Q(organization__path__startswith=org.path) &
                Q(organization__depth__gt=org.depth) &
                Q(created__date__lte=date_1)
            )
        ]

    if user.is_staff or user.is_superuser:
        args += [
            # 4. Superuser can see all tasks created later than
            Q(created__date__lte=date_2)
        ]
    query = functools.reduce(operator.or_, args)

    # By default, we are only interested in open tasks.
    query = functools.reduce(operator.and_, [query, Q(status__in=[Task.CREATED, Task.ASSIGNED])])
    return queryset.filter(query)
