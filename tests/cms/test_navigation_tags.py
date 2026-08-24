import pytest
from cms.api import create_page
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils.translation import get_language

from vitrina.templatetags.navigation_tags import menu_cache_key, show_menu


@pytest.mark.django_db
def test_show_menu_does_not_query_when_cached():
    show_menu()

    with CaptureQueriesContext(connection) as second:
        show_menu()

    assert len(second) == 0, f"show_menu made {len(second)} queries on the second call"


@pytest.mark.django_db
def test_show_menu_cache_clears_when_a_page_changes(django_capture_on_commit_callbacks):
    show_menu()
    assert cache.get(menu_cache_key(get_language())) is not None

    with django_capture_on_commit_callbacks(execute=True):
        create_page("Naujas puslapis", "pages/page.html", get_language(), in_navigation=True)

    assert cache.get(menu_cache_key(get_language())) is None
