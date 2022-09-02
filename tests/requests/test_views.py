import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp, WebTest

from vitrina.datasets.factories import DatasetFactory
from vitrina.requests.factories import RequestFactory


class RequestDetailTest(WebTest):
    def setUp(self):
        self.dataset = DatasetFactory()
        self.request = RequestFactory(
            dataset_id=self.dataset.pk,
            is_existing=True,
            status="REJECTED",
            purpose="science,product",
            changes="format",
            format="csv, json, rdf",
            structure_data=(
                "data1,dictionary1,type1,notes1;"
                "data2,dictionary2,type2,notes2"
            )
        )

    def test_context(self):
        resp = self.app.get(reverse('request-detail', args=[self.request.pk]))
        self.assertEqual(resp.context['status'], "Atmestas")
        self.assertEqual(resp.context['purposes'], ['science', 'product'])
        self.assertEqual(resp.context['changes'], ['format'])
        self.assertEqual(resp.context['formats'], ['csv', 'json', 'rdf'])
        self.assertEqual(resp.context['like_count'], 0)
        self.assertFalse(resp.context['liked'])
        self.assertEqual(resp.context['structure'], [
            {
                "data_title": 'data1',
                "dictionary_title": 'dictionary1',
                "data_type": 'type1',
                "data_notes": 'notes1',
            },
            {
                "data_title": 'data2',
                "dictionary_title": 'dictionary2',
                "data_type": 'type2',
                "data_notes": 'notes2',
            }
        ])
