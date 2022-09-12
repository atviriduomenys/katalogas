from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StructureConfig(AppConfig):
    name = 'vitrina.compat'
    label = 'vitrina_compat'
    verbose_name = _("Compat")
