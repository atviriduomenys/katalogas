from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from django.test import RequestFactory
from django_webtest import DjangoTestApp

from vitrina.datasets.views import DatasetStatsView
from vitrina.users.views import UserStatsView


def test_stats_cache_key_includes_query_parameters(rf: RequestFactory):
    request = rf.get(reverse("dataset-stats-status") + "?format=json&selected_facets=status_exact:HAS_DATA")
    view = DatasetStatsView()
    view.request = request

    cache_key = view.get_stats_cache_key()

    assert "selected_facets=status_exact%3AHAS_DATA" in cache_key
    assert "format=json" not in cache_key


def test_stats_cache_key_differs_for_different_urls(rf: RequestFactory):
    view = DatasetStatsView()

    request1 = rf.get(reverse("dataset-stats-status") + "?format=json&selected_facets=status_exact:HAS_DATA")
    view.request = request1
    key1 = view.get_stats_cache_key()

    request2 = rf.get(reverse("dataset-stats-status") + "?format=json&selected_facets=status_exact:HAS_DATA&q=test")
    view.request = request2
    key2 = view.get_stats_cache_key()

    assert key1 != key2


def test_stats_are_cached(app: DjangoTestApp, rf: RequestFactory):
    cache.clear()

    url = reverse("dataset-stats-status") + "?format=json"
    expected_data = [{"label": "Test", "data": []}]

    with patch.object(
        DatasetStatsView,
        "update_context_data",
        autospec=True,
    ) as update_context:
        update_context.side_effect = lambda self, context: {
            **context,
            "time_chart_data": expected_data,
        }

        response1 = app.get(url)

        request = rf.get(url)
        view = DatasetStatsView()
        view.request = request
        cache_key = view.get_stats_cache_key()

        assert response1.json == {"datasets": expected_data}
        assert cache.get(cache_key) == expected_data
        assert update_context.call_count == 1

        response2 = app.get(url)

        assert response2.json == {"datasets": expected_data}
        assert update_context.call_count == 1


def test_stats_are_not_cached(app: DjangoTestApp, rf: RequestFactory):
    cache.clear()

    url = reverse("dataset-stats-status")
    original_method = DatasetStatsView.update_context_data

    with patch.object(
        DatasetStatsView,
        "update_context_data",
        autospec=True,
        side_effect=original_method,
    ) as update_context:
        app.get(url)
        app.get(url)

        request = rf.get(url)
        view = DatasetStatsView()
        view.request = request
        cache_key = view.get_stats_cache_key()

        assert update_context.call_count == 2
        assert cache.get(cache_key) is None


def test_user_stats_are_cached(app: DjangoTestApp):
    cache.clear()

    url = reverse("users-stats-graph") + "?format=json"
    expected_data = [{"label": "Test", "data": []}]

    with patch.object(UserStatsView, "get_data", return_value=expected_data) as get_data:
        response1 = app.get(url)

        assert response1.json == {"data": expected_data}
        assert cache.get("user_stats_chart_data") == expected_data
        assert get_data.call_count == 1

        response2 = app.get(url)

        assert response2.json == {"data": expected_data}
        assert get_data.call_count == 1


def test_user_stats_are_not_cached(app: DjangoTestApp):
    cache.clear()

    url = reverse("users-stats-graph")

    with patch.object(UserStatsView, "get_data", return_value={}) as get_data:
        app.get(url)
        app.get(url)

        assert get_data.call_count == 2
        assert cache.get("user_stats_chart_data") is None
