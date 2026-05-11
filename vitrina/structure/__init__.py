from django.db import models
from django.utils.translation import gettext_lazy as _


class VersionStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Juodraštis")
    PRE_RELEASE = "PRE_RELEASE", _("Išankstinis leidimas")
    STABLE = "STABLE", _("Stabili")
    DEPRECATED = "DEPRECATED", _("Pasenusi")
    WITHDRAWN = "WITHDRAWN", _("Atsisakyta")
    DELETED = "DELETED", _("Ištrinta")
    DESTROYED = "DESTROYED", _("Sunaikinta")
    TESTING = "TESTING", _("Tikrinama")
    DEPLOYING = "DEPLOYING", _("Diegiama")


class VersionType(models.TextChoices):
    MAJOR = "MAJOR", _("Pagrindinė")
    MINOR = "MINOR", _("Papildoma")
    PATCH = "PATCH", _("Pataisa")


class AccessType(models.IntegerChoices):
    PRIVATE = 0, _("private")
    PROTECTED = 1, _("protected")
    PUBLIC = 2, _("public")
    OPEN = 3, _("open")


class UMLDiagramStatus(models.TextChoices):
    OUTDATED = "OUTDATED", "Outdated"
    PENDING = "PENDING", "Pending"
    UP_TO_DATE = "UP_TO_DATE", "Up to date"
