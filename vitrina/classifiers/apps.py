from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ClassifiersConfig(AppConfig):
    name = 'vitrina.classifiers'
    label = 'vitrina_classifiers'
    verbose_name = _("Classifiers")
