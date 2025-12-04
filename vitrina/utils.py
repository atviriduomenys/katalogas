import logging
import requests
from vitrina.settings import TRANSLATION_CLIENT_ID, TRANSLATION_URL, TRANSLATION_REQUEST_TIMEOUT
from dataclasses import dataclass, field, asdict
from django.core.serializers.json import DjangoJSONEncoder
import json
from enum import StrEnum
from typing import Any


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


class RevisionSource(StrEnum):
    VIEW = "view"
    ADMIN = "admin"
    TASK = "task"


@dataclass
class RevisionComment:
    source: RevisionSource
    action: str | None = None
    view: str | None = None
    http_method: str | None = None
    path: str | None = None
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        data = asdict(self)
        data["source"] = self.source.value
        return json.dumps(data, cls=DjangoJSONEncoder)

    @classmethod
    def from_json(cls, raw: str) -> "RevisionComment | None":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        source_value = data.get("source", RevisionSource.VIEW)
        try:
            data["source"] = RevisionSource(source_value)
        except ValueError:
            data["source"] = RevisionSource.VIEW
        return cls(**data)