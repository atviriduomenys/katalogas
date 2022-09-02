from datetime import datetime

from django.urls import reverse
from django_webtest import WebTest

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset


class DatasetSearchTest(WebTest):
    def setUp(self):
        self.dataset1 = DatasetFactory(
            title="Duomenų rinkinys 1",
            title_en="Dataset 1",
            published=datetime(2022, 6, 1)
        )
        self.dataset2 = DatasetFactory(
            title="Duomenų rinkinys 2 \"<'>\\",
            title_en="Dataset 2",
            published=datetime(2022, 8, 1)
        )
        self.dataset3 = DatasetFactory(
            title="Duomenų rinkinys 3",
            title_en="Dataset 3",
            published=datetime(2022, 7, 1)
        )

    def test_without_query(self):
        resp = self.app.get(reverse('dataset-list'))
        self.assertEqual(list(resp.context['object_list']), [self.dataset2, self.dataset3, self.dataset1])

    def test_with_query_that_doesnt_match(self):
        resp = self.app.get("%s?q=%s" % (reverse('dataset-list'), "doesnt-match"))
        self.assertEqual(len(resp.context['object_list']), 0)

    def test_with_query_that_matches_one(self):
        resp = self.app.get("%s?q=%s" % (reverse('dataset-list'), "1"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1])

    def test_with_query_that_matches_all(self):
        resp = self.app.get("%s?q=%s" % (reverse('dataset-list'), "rinkinys"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset2, self.dataset3, self.dataset1])

    def test_with_query_that_matches_all_with_english_title(self):
        resp = self.app.get("%s?q=%s" % (reverse('dataset-list'), "dataset"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset2, self.dataset3, self.dataset1])

    def test_with_query_containing_special_characters(self):
        resp = self.app.get("%s?q=%s" % (reverse('dataset-list'), "\"<'>\\"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset2])
