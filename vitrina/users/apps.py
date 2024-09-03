from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = 'vitrina.users'
    label = 'vitrina_users'
    verbose_name = _("Visi naudotojai")
