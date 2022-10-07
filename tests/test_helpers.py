from unittest.mock import Mock

import pytest
from django.test import RequestFactory

from vitrina.helpers import get_selected_value, get_filter_url


@pytest.mark.django_db
def test_get_selected_value():
    facet_form = Mock(selected_facets=['key_exact:value'])
    selected_value = get_selected_value(facet_form, 'key', is_int=False)
    assert selected_value == 'value'


@pytest.mark.django_db
def test_get_selected_value_multiple():
    facet_form = Mock(selected_facets=['key_exact:value1', 'key_exact:value2'])
    selected_value = get_selected_value(facet_form, 'key', multiple=True, is_int=False)
    assert selected_value == ['value1', 'value2']


@pytest.mark.django_db
def test_get_selected_value_int():
    facet_form = Mock(selected_facets=['key_exact:1'])
    selected_value = get_selected_value(facet_form, 'key')
    assert selected_value == 1


@pytest.mark.django_db
def test_get_selected_value_multiple_int():
    facet_form = Mock(selected_facets=['key_exact:1', 'key_exact:2'])
    selected_value = get_selected_value(facet_form, 'key', multiple=True)
    assert selected_value == [1, 2]


@pytest.mark.django_db
def test_get_selected_value_int_value_error(rf: RequestFactory):
    facet_form = Mock(selected_facets=['key_exact:?'])
    selected_value = get_selected_value(facet_form, 'key')
    assert selected_value is None


@pytest.mark.django_db
def test_get_filter_url(rf: RequestFactory):
    request = rf.get('/')
    filter_url = get_filter_url(request, 'key', 'value')
    assert filter_url == "?selected_facets=key_exact%3Avalue"


@pytest.mark.django_db
def test_get_filter_url_with_existing_key(rf: RequestFactory):
    request = rf.get('/', {"selected_facets": "key1_exact:value1"})
    filter_url = get_filter_url(request, 'key2', 'value2')
    assert filter_url == "?selected_facets=key1_exact%3Avalue1&selected_facets=key2_exact%3Avalue2"


@pytest.mark.django_db
def test_get_filter_url_with_page(rf: RequestFactory):
    request = rf.get('/', {"page": "1"})
    filter_url = get_filter_url(request, 'key', 'value')
    assert filter_url == "?selected_facets=key_exact%3Avalue"


