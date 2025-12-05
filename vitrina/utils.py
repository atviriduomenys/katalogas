import logging
import requests
from vitrina.settings import TRANSLATION_CLIENT_ID, TRANSLATION_URL, TRANSLATION_REQUEST_TIMEOUT
from django.conf import settings
from fnmatch import fnmatchcase
from django.db import models
from django.apps import apps

logger = logging.getLogger()


def translate_text(text: str, field_name: str = "") -> str | None:
    if not text:
        return None

    try:
        response = requests.post(
            TRANSLATION_URL,
            json={
                "appId": "",
                "systemID": "smt-8abc06a7-09dc-405c-bd29-580edc74eb05",
                "text": text,
                "options": "",
            },
            headers={
                "client-id": TRANSLATION_CLIENT_ID,
                "Content-Type": "application/json; charset=utf-8",
            },
            timeout=TRANSLATION_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.warning(f"Translation timeout for {field_name}")
        return text
    except requests.exceptions.RequestException as e:
        logger.warning(f"Translation failed for {field_name}: {e}")
        return text
    except (ValueError, KeyError) as e:
        logger.error(f"Invalid translation response for {field_name}: {e}")
        return text
    except Exception as e:
        logger.exception(f"Unexpected error during translation for {field_name}: {e}")
        return text


def is_model_versioned(model: type[models.Model]) -> bool:
    if model not in get_all_models(app_prefix="vitrina"):
        return False
    excluded_models_patterns = settings.NOT_VERSIONED_MODELS
    full_name = f"{model.__module__}.{model.__name__}"
    return not any(fnmatchcase(full_name, pattern) for pattern in excluded_models_patterns)


def get_all_models(
    app_prefix: str | None = None, include_proxy: bool = True, include_unmanaged: bool = False
) -> set[type[models.Model]]:
    project_models = set()
    for app_config in apps.get_app_configs():
        if app_prefix and not app_config.name.startswith(app_prefix):
            continue

        for model in app_config.get_models():
            if not include_proxy and model._meta.proxy:
                continue
            if not include_unmanaged and not model._meta.managed:
                continue

            project_models.add(model)
    return project_models
