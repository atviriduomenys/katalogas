from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

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

    CREATED = "created"
    COMPLETED = "completed"
    STATUSES = (
        (CREATED, _("Sukurta")),
        (COMPLETED, _("Atlikta"))
    )

    title = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(to=User, blank=True, null=True, on_delete=models.SET_NULL)
    organization = models.ForeignKey(to=Organization, blank=True, null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=255, default=CREATED, choices=STATUSES)
    role = models.CharField(choices=ROLES, max_length=255, blank=True, null=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'task'

    def __str__(self):
        return self.title


class Holiday(models.Model):
    title = models.CharField(max_length=255)
    date = models.DateField(unique=True)

    class Meta:
        db_table = 'holiday'
