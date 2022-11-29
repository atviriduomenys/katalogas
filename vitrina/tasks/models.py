from datetime import datetime

from django.db import models

from vitrina.orgs.models import Organization
from vitrina.users.models import User

from django.utils.translation import gettext_lazy as _
from django.utils.timezone import utc

now = datetime.utcnow().replace(tzinfo=utc)


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

    class Meta:
        db_table = 'task'
