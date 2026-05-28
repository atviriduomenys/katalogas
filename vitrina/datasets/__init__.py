from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactKind(models.TextChoices):
    INDIVIDUAL = "individual", _("Registruotas naudotojas")
    ORG = "org", _("Organizacija")
    UNREGISTERED = "unregistered", _("Neregistruotas naudotojas")
    SERVICE = "service", _("Paslauga")
