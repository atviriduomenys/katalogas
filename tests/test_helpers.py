import pytest
from django.test import RequestFactory

from vitrina.helpers import get_selected_value, get_filter_url


@pytest.mark.django_db
def test_get_selected_value(rf: RequestFactory):
    request = rf.get('/', {'key': 'value'})
    selected_value = get_selected_value(request, 'key', is_int=False)
    assert selected_value == 'value'


@pytest.mark.django_db
def test_get_selected_value_multiple(rf: RequestFactory):
    request = rf.get('/', {'key': ['value1', 'value2']})
    selected_value = get_selected_value(request, 'key', multiple=True, is_int=False)
    assert selected_value == ['value1', 'value2']


@pytest.mark.django_db
def test_get_selected_value_int(rf: RequestFactory):
    request = rf.get('/', {'key': '1'})
    selected_value = get_selected_value(request, 'key')
    assert selected_value == 1


@pytest.mark.django_db
def test_get_selected_value_multiple_int(rf: RequestFactory):
    request = rf.get('/', {'key': ['1', '2']})
    selected_value = get_selected_value(request, 'key', multiple=True)
    assert selected_value == [1, 2]


@pytest.mark.django_db
def test_get_selected_value_int_value_error(rf: RequestFactory):
    request = rf.get('/', {'key': '?'})
    selected_value = get_selected_value(request, 'key')
    assert selected_value is None


@pytest.mark.django_db
def test_get_filter_url(rf: RequestFactory):
    request = rf.get('/')
    filter_url = get_filter_url(request, 'key', 'value')
    assert filter_url == "?key=value"


@pytest.mark.django_db
def test_get_filter_url_with_append(rf: RequestFactory):
    request = rf.get('/')
    filter_url = get_filter_url(request, 'key', 'value', append=True)
    assert filter_url == "?key=value"


@pytest.mark.django_db
def test_get_filter_url_with_append_and_existing_key(rf: RequestFactory):
    request = rf.get('/', {"key1": "value1"})
    filter_url = get_filter_url(request, 'key2', 'value2', append=True)
    assert filter_url == "?key1=value1&key2=value2"


