from datetime import datetime, timezone

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

import numpy as np
import pandas as pd

from vitrina.comments.models import Comment
from vitrina.orgs.models import Organization
from vitrina.users.models import User

from django.utils.translation import gettext_lazy as _


def get_due_date():
    due_date = datetime.now(timezone.utc) + pd.offsets.BusinessDay(n=5)
    return due_date


class Task(models.Model):
    SUPERVISOR = 'supervisor'
    COORDINATOR = 'coordinator'
    MANAGER = 'manager'
    ROLES = {
        (SUPERVISOR, _("Vyr. koordinatorius")),
        (COORDINATOR, _("Organizacijos koordinatorius")),
        (MANAGER, _("Organizacijos tvarkytojas"))
    }

    COMMENT = 'comment'
    REQUEST = 'request'
    ERROR = 'error'
    ERROR_FREQUENCY = 'error_frequency'
    ERROR_DISTRIBUTION = 'error_distribution'
    TYPES = (
        (COMMENT, _("Komentaras")),
        (REQUEST, _("Prašymas")),
        (ERROR, _("Klaida")),
        (ERROR_FREQUENCY, _("Klaida atnaujinimo dažnume")),
        (ERROR_DISTRIBUTION, _("Klaida duomenų rinkinio duomenų šaltinyje")),
    )

    CREATED = "created"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    STATUSES = (
        (CREATED, _("Registruota")),
        (ASSIGNED, _("Priskirta")),
        (COMPLETED, _("Išspręsta"))
    )

    title = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(to=User, blank=True, null=True, on_delete=models.SET_NULL)
    organization = models.ForeignKey(to=Organization, blank=True, null=True, on_delete=models.SET_NULL)
    comment_object = models.ForeignKey(to=Comment, blank=True, null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=255, default=CREATED, choices=STATUSES)
    type = models.CharField(max_length=255, choices=TYPES, default=COMMENT)
    role = models.CharField(choices=ROLES, max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    assigned = models.DateTimeField(blank=True, null=True)
    completed = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    # comments = GenericRelation('vitrina_comments.Comment')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'task'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.due_date = get_due_date()
        super(Task, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('user-task-detail', kwargs={
            'pk': self.user.pk,
            'task_id': self.pk
        })

    def is_due_or_expiring(self):
        due = pd.to_datetime(self.due_date).date()
        now = datetime.now(timezone.utc).date()
        if self.status != Task.COMPLETED:
            diff = (due - now).days
            days = np.busday_count(due, now)
            if diff < 0:
                return [True, days]
            elif 3 >= diff > 0:
                return [False, abs(days)]
        else:
            return False

    def get_acl_parents(self):
        return [self]


class Holiday(models.Model):
    title = models.CharField(max_length=255)
    date = models.DateField(unique=True)

    class Meta:
        db_table = 'holiday'
