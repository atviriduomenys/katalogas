from django.urls import reverse
from django_webtest import WebTest

from vitrina.datasets.factories import DatasetFactory


class DatasetDetailTest(WebTest):
    def setUp(self):
        self.dataset = DatasetFactory(status="HAS_DATA")

    def test_without_tags(self):
        resp = self.app.get(reverse('dataset-detail', args=[self.dataset.slug]))
        self.assertEqual(resp.context['tags'], [])

    def test_tags(self):
        self.dataset.tags = "tag-1, tag-2, tag-3"
        self.dataset.save()
        resp = self.app.get(reverse('dataset-detail', args=[self.dataset.slug]))
        self.assertEqual(resp.context['tags'], ['tag-1', 'tag-2', 'tag-3'])

    def test_status(self):
        resp = self.app.get(reverse('dataset-detail', args=[self.dataset.slug]))
        self.assertEqual(resp.context['status'], "Atvertas")

    def test_other_context_data(self):
        resp = self.app.get(reverse('dataset-detail', args=[self.dataset.slug]))

        # hardcoded values, will need to change with later tasks
        self.assertEqual(resp.context['subscription'], [])
        self.assertEqual(resp.context['rating'], 3.0)
