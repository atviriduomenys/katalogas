import pytest
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from vitrina.utils import get_all_models, is_model_versioned
from django.contrib import admin
from vitrina.admin import RevisionCommentVersionAdmin

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


@pytest.mark.django_db
def test_versioned_models_inherit_revision_comment_admin_class():
    for model in get_all_models():
        model_admin_instance = admin.site._registry.get(model)
        if model_admin_instance is None:
            continue
        if is_model_versioned(model):
            assert isinstance(model_admin_instance, RevisionCommentVersionAdmin), (
                f"Model '{model.__module__}.{model.__name__}' is versioned and registered "
                f"with django admin, but does not inherit "
                f"'RevisionCommentVersionAdmin' class."
            )
