from django.apps import AppConfig, apps
import reversion
from django.db.utils import OperationalError, ProgrammingError
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from fnmatch import fnmatch


NOT_VERSIONED_MODELS = (
    "vitrina.users.models.*",
    "vitrina.cms.models.CmsAttachment",
    ...
)


class ApiConfig(AppConfig):
    name = "vitrina"
    label = "vitrina"

    def ready(self):
        super().ready()
        self.register_all_project_models_for_reversion()

    def register_all_project_models_for_reversion(self):
        project_prefix = self.name

        try:
            for app_config in apps.get_app_configs():
                if not app_config.name.startswith(project_prefix):
                    continue
                
                versioned_models: list[models.Model] = app_config.get_models()
                for model in versioned_models:
                    if model._meta.proxy or not model._meta.managed:
                        continue

                    try:
                        reversion.register(model)
                    except reversion.RegistrationError:
                        # If model is already registered
                        pass

        except (OperationalError, ProgrammingError):
            pass
