import json

from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import resolve
from django.views import View


FROZEN_NOW = "2023-06-15 12:00:00"


def get_stats_context(
    view_class: type[View],
    path: str,
    *,
    params: dict[str, Any] | None = None,
    user: AbstractBaseUser | AnonymousUser | None = None,
    **view_kwargs: Any,
) -> dict:
    request = RequestFactory().get(path, data=params or {})
    request.user = user or AnonymousUser()
    request.LANGUAGE_CODE = getattr(settings, "LANGUAGE_CODE", "lt")
    request.session = {}
    request.resolver_match = resolve(path)
    response = view_class.as_view()(request, **view_kwargs)
    return response.context_data


DURATIONS = [
    "duration-yearly",
    "duration-quarterly",
    "duration-monthly",
    "duration-weekly",
    "duration-daily",
]


def normalize_chart_snapshot(snapshot: Mapping[str, Any]) -> dict:
    bar = sorted(snapshot["bar_chart_data"], key=lambda x: x["display_value"])
    tcd = sorted(json.loads(snapshot["time_chart_data"]), key=lambda x: x["label"])
    return {
        "time_chart_data": json.dumps(tcd, ensure_ascii=False),
        "bar_chart_data": bar,
        "max_count": snapshot["max_count"],
    }
