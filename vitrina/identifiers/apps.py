from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class IdentifiersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vitrina.identifiers"
    label = "vitrina_identifiers"
    verbose_name = _("Identifikatoriai")
