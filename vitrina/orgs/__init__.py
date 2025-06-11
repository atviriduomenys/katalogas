from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class AgentType(TextChoices):
    SPINTA = "SPINTA", "Spinta"
    OTHER = "OTHER", _("Kita")
