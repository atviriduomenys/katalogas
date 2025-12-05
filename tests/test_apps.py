import pytest
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from vitrina.utils import get_all_models, is_model_versioned

import reversion


def test_reversion_all_models_registered_or_excluded():
    for model in get_all_models():
        path = f"{model.__module__}.{model.__name__}"
        is_versioned = is_model_versioned(model)

        if is_versioned:
            assert reversion.is_registered(model), f"Model '{path}' should be registered with reversion."
        else:
            assert not reversion.is_registered(model), f"Model '{path}' should not be registered with reversion."


@override_settings(NOT_VERSIONED_MODELS=["notExistingModel"])
def test_not_existing_model_in_not_versioned_models():
    api_config = apps.get_app_config("vitrina")

    with pytest.raises(
        ImproperlyConfigured, match="The NOT_VERSIONED_MODELS pattern 'notExistingModel' does not match any models."
    ):
        api_config.ready()
