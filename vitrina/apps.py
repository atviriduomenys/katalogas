import logging
from django.apps import AppConfig
import reversion
from django.core.exceptions import ImproperlyConfigured
from fnmatch import fnmatchcase
from django.db import models
from django.conf import settings
from vitrina.utils import get_all_models, is_model_versioned


logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    name = "vitrina"
    label = "vitrina"

    def ready(self) -> None:
        super().ready()
        eligible_models = get_all_models(app_prefix="vitrina")
        if settings.DEBUG:
            self._validate_not_versioned_patterns(eligible_models)
        versioned_models = {model for model in eligible_models if is_model_versioned(model)}
        self._register_models_for_reversion(versioned_models)

    def _register_models_for_reversion(self, versioned_models: set[type[models.Model]]) -> None:
        for model in versioned_models:
            if not reversion.is_registered(model):
                reversion.register(model)

    def _validate_not_versioned_patterns(self, project_models: set[type[models.Model]]) -> None:
        patterns = settings.NOT_VERSIONED_MODELS
        for pattern in patterns:
            if not any(fnmatchcase(f"{model.__module__}.{model.__name__}", pattern) for model in project_models):
                raise ImproperlyConfigured(f"The NOT_VERSIONED_MODELS pattern '{pattern}' does not match any models.")
