import json as _json

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import resolve


FROZEN_NOW = "2023-06-15 12:00:00"


def get_stats_context(view_class, path, *, params=None, user=None, **view_kwargs):
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


def normalize_chart_snapshot(snapshot):
    bar = sorted(snapshot["bar_chart_data"], key=lambda x: x["display_value"])
    tcd = sorted(_json.loads(snapshot["time_chart_data"]), key=lambda x: x["label"])
    return {
        "time_chart_data": _json.dumps(tcd, ensure_ascii=False),
        "bar_chart_data": bar,
        "max_count": snapshot["max_count"],
    }
