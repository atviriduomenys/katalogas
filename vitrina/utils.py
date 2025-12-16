import logging
import requests
import json
from enum import StrEnum
from typing import Any
from dataclasses import dataclass, field, asdict
from vitrina.settings import TRANSLATION_CLIENT_ID, TRANSLATION_URL, TRANSLATION_REQUEST_TIMEOUT
from django.conf import settings
from fnmatch import fnmatchcase
from django.db import models
from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder


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
    """Return whether the given Django model should be treated as versioned.

    A model is considered versioned if:
    - it belongs to an installed app whose dotted name starts with "vitrina" (via `get_all_models()`), and
    - its fully-qualified name (<module>.<class>) does not match any pattern in
      `settings.NOT_VERSIONED_MODELS`.
    """
    if model not in get_all_models(app_prefix="vitrina"):
        return False

    full_name = f"{model.__module__}.{model.__name__}"
    return not any(fnmatchcase(full_name, pattern) for pattern in settings.NOT_VERSIONED_MODELS)


def get_all_models(
    app_prefix: str | None = None, include_proxy: bool = True, include_unmanaged: bool = False
) -> set[type[models.Model]]:
    """Return a set of Django model classes from installed apps, with optional filtering."""
    project_models = set()
    for model in apps.get_models():
        if app_prefix and not model._meta.app_config.name.startswith(app_prefix):
            continue

        if not include_proxy and model._meta.proxy:
            continue
        if not include_unmanaged and not model._meta.managed:
            continue

        project_models.add(model)
    return project_models


class RevisionSource(StrEnum):
    """Indicates where a revision change originated from."""

    VIEW = "view"  # katalogas UI or UAPI
    ADMIN = "admin"  # Django admin
    TASK = "task"  # Background jobs (Celery, etc.)


@dataclass
class RevisionComment:
    source: RevisionSource
    action: str | None = None
    http_method: str | None = None
    path: str | None = None
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        data = asdict(self)
        data["source"] = self.source.value
        return json.dumps(data, cls=DjangoJSONEncoder)

    @classmethod
    def from_json(cls, raw_json: str) -> "RevisionComment | None":
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return None

        if "source" not in data:
            raise ValueError("Missing 'source' in revision comment")

        try:
            data["source"] = RevisionSource(data["source"])
        except ValueError as exception:
            raise ValueError(f"Invalid source value: {data['source']}") from exception

        return cls(**data)
