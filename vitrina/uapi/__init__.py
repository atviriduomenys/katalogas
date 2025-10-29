from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class AgentType(TextChoices):
    SPINTA = "SPINTA", "Spinta"
    OTHER = "OTHER", _("Kita")


class HTTPMethods(TextChoices):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class PossibleResults(TextChoices):
    FAILED = "FAILED", _("Nesėkminga")
    UPDATED = "UPDATED", _("Atnaujinta")
    UPDATED_WITH_CONFLICT = "UPDATED_WITH_CONFLICT", _("Atnaujinta su konfliktu")
    UPDATED_WITHOUT_CHANGES = "UPDATED_WITHOUT_CHANGES", _("Atnaujinta be pakeitimų")
    STATUS_ALIVE = "STATUS_ALIVE", _("Veikianti būsena")
    STATUS_ERROR = "STATUS_ERROR", _("Klaidinga būsena")


class ChangedBy(TextChoices):
    AGENT = "AGENT", _("Agentas")
    ADMIN = "ADMIN", _("Administratorius")


class ChangeType(TextChoices):
    CREATE = "CREATE", _("Sukurti")
    UPDATE = "UPDATE", _("Atnaujinti")
    DELETE = "DELETE", _("Ištrinti")


class Environment(TextChoices):
    DEVELOPMENT = "DEVELOPMENT", _("Vystymo")
    TESTING = "TESTING", _("Testavimo")
    PRODUCTION = "PRODUCTION", _("Gamybinė")
