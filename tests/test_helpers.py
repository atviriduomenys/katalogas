from django.test import RequestFactory
from django_webtest import WebTest

from vitrina.helpers import get_selected_value, get_filter_url


class SelectedValueTest(WebTest):
    def setUp(self):
        self.rf = RequestFactory()

    def test_get_selected_value(self):
        request = self.rf.get('/', {'key': 'value'})
        selected_value = get_selected_value(request, 'key', is_int=False)
        self.assertEqual(selected_value, 'value')

    def test_get_selected_value_multiple(self):
        request = self.rf.get('/', {'key': ['value1', 'value2']})
        selected_value = get_selected_value(request, 'key', multiple=True, is_int=False)
        self.assertEqual(selected_value, ['value1', 'value2'])

    def test_get_selected_value_int(self):
        request = self.rf.get('/', {'key': '1'})
        selected_value = get_selected_value(request, 'key')
        self.assertEqual(selected_value, 1)

    def test_get_selected_value_multiple_int(self):
        request = self.rf.get('/', {'key': ['1', '2']})
        selected_value = get_selected_value(request, 'key', multiple=True)
        self.assertEqual(selected_value, [1, 2])

    def test_get_selected_value_int_value_error(self):
        request = self.rf.get('/', {'key': '?'})
        selected_value = get_selected_value(request, 'key')
        self.assertIsNone(selected_value)


class FilterUrlTest(WebTest):
    def setUp(self):
        self.rf = RequestFactory()

    def test_get_filter_url(self):
        request = self.rf.get('/')
        filter_url = get_filter_url(request, 'key', 'value')
        self.assertEqual(filter_url, "?key=value")

    def test_get_filter_url_with_append(self):
        request = self.rf.get('/')
        filter_url = get_filter_url(request, 'key', 'value', append=True)
        self.assertEqual(filter_url, "?key=value")

    def test_get_filter_url_with_append_and_existing_key(self):
        request = self.rf.get('/', {"key1": "value1"})
        filter_url = get_filter_url(request, 'key2', 'value2', append=True)
        self.assertEqual(filter_url, "?key1=value1&key2=value2")


