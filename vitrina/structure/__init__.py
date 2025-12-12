from django.db import models
from django.utils.translation import gettext_lazy as _

from vitrina.datasets.structure import Enum, Base, Property, Model
from vitrina.structure.models import ParamItem, Param, EnumItem


RELATED_OBJECT_TYPE = Model | Property | Base | EnumItem | Enum | Param | ParamItem


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
