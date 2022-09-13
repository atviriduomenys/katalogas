from datetime import datetime

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

    title = models.CharField(max_length=255)
    created = models.DateTimeField(default=datetime.now)
    user = models.ForeignKey(to=User, blank=True, null=True, on_delete=models.SET_NULL)
    role = models.CharField(max_length=255, choices=ROLES, blank=True, null=True)
    organization = models.ForeignKey(to=Organization, blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'task'
