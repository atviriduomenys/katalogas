from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from vitrina.orgs.models import Organization
from vitrina.users.models import User

from django.utils.translation import gettext_lazy as _


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
    TYPES = (
        (COMMENT, _("Komentaras")),
        (REQUEST, _("Prašymas")),
        (ERROR, _("Klaida")),
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
    status = models.CharField(max_length=255, default=CREATED, choices=STATUSES)
    type = models.CharField(max_length=255, choices=TYPES, default=COMMENT)
    role = models.CharField(choices=ROLES, max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)

    comments = GenericRelation('vitrina_comments.Comment')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'task'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('user-task-detail', kwargs={
            'pk': self.user.pk,
            'task_id': self.pk
        })

    def get_acl_parents(self):
        return [self]


class Holiday(models.Model):
    title = models.CharField(max_length=255)
    date = models.DateField(unique=True)

    class Meta:
        db_table = 'holiday'
