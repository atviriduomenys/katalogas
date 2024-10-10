from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OrgsConfig(AppConfig):
    name = 'vitrina.orgs'
    label = 'vitrina_orgs'
    verbose_name = _("Organizacijos")
