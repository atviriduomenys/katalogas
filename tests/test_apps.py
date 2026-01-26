import pytest
from django.apps import apps
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from vitrina.utils import get_all_models, is_model_versioned
from django.contrib import admin
from vitrina.admin import RevisionCommentVersionAdmin

import reversion


@pytest.mark.parametrize(
    "model, should_be_registered",
    [(model, is_model_versioned(model)) for model in get_all_models()],
)
def test_reversion_model_registration(model: type[models.Model], should_be_registered: bool):
    path = f"{model.__module__}.{model.__name__}"

    if should_be_registered:
        assert reversion.is_registered(model), f"Model '{path}' should be registered with reversion."
    else:
        assert not reversion.is_registered(model), f"Model '{path}' should not be registered with reversion."


@override_settings(NOT_VERSIONED_MODELS=["notExistingModel"], DEBUG=True)
def test_not_existing_model_in_not_versioned_models():
    api_config = apps.get_app_config("vitrina")

    with pytest.raises(
        ImproperlyConfigured, match="The NOT_VERSIONED_MODELS pattern 'notExistingModel' does not match any models."
    ):
        api_config.ready()


@pytest.mark.parametrize("versioned_model", [model for model in get_all_models() if is_model_versioned(model)])
@pytest.mark.django_db
def test_versioned_models_inherit_revision_comment_admin_class(versioned_model: type[models.Model]):
    if model_admin_instance := admin.site._registry.get(versioned_model):
        assert isinstance(model_admin_instance, RevisionCommentVersionAdmin), (
            f"Model '{versioned_model.__module__}.{versioned_model.__name__}' is versioned and registered "
            f"with django admin, but does not inherit "
            f"'RevisionCommentVersionAdmin' class."
        )
