from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class AgreementStatuses(TextChoices):
    CREATED = "CREATED", _("Pateikta")
    FORMED = "FORMED", _("Suformuota")
    INITIATED = "INITIATED", _("Inicijuota")
    SIGNED = "SIGNED", _("Pasirašyta")
    ACTIVE = "ACTIVE", _("Aktyvi")
    TERMINATED = "TERMINATED", _("Nutraukta")
