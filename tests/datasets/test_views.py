from datetime import datetime

from django.urls import reverse
from django_webtest import WebTest

from vitrina.classifiers.factories import CategoryFactory, FrequencyFactory
from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory


class StatusFilterTest(WebTest):
    def setUp(self):
        self.dataset1 = DatasetFactory(status=Dataset.HAS_DATA)
        self.dataset2 = DatasetFactory()
        DatasetStructureFactory(dataset=self.dataset2)

    def test_without_query(self):
        resp = self.app.get(reverse('dataset-list'))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1, self.dataset2])
        self.assertIsNone(resp.context['selected_status'])

    def test_has_data(self):
        resp = self.app.get("%s?status=%s" % (reverse('dataset-list'), Dataset.HAS_DATA))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1])
        self.assertEqual(resp.context['selected_status'], Dataset.HAS_DATA)

    def test_has_structure(self):
        resp = self.app.get("%s?status=%s" % (reverse('dataset-list'), Dataset.HAS_STRUCTURE))
        self.assertEqual(list(resp.context['object_list']), [self.dataset2])
        self.assertEqual(resp.context['selected_status'], Dataset.HAS_STRUCTURE)


class OrganizationFilterTest(WebTest):
    def setUp(self):
        self.organization = OrganizationFactory()
        self.dataset1 = DatasetFactory(organization=self.organization)
        self.dataset2 = DatasetFactory(organization=self.organization)

    def test_without_query(self):
        resp = self.app.get(reverse('dataset-list'))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1, self.dataset2])
        self.assertIsNone(resp.context['selected_organization'])

    def test_with_organization(self):
        resp = self.app.get("%s?organization=%s" % (reverse("dataset-list"), self.organization.pk))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1, self.dataset2])
        self.assertEqual(resp.context['selected_organization'], self.organization.pk)


class CategoryFilterTest(WebTest):
    def setUp(self):
        self.category1 = CategoryFactory()
        self.category2 = CategoryFactory(parent=self.category1)
        self.category3 = CategoryFactory(parent=self.category1)
        self.category4 = CategoryFactory(parent=self.category2)
        self.dataset1 = DatasetFactory(category=self.category1)
        self.dataset2 = DatasetFactory(category=self.category2)
        self.dataset3 = DatasetFactory(category=self.category3)
        self.dataset4 = DatasetFactory(category=self.category4)

    def test_without_query(self):
        resp = self.app.get(reverse('dataset-list'))
        self.assertEqual(len(resp.context['object_list']), 4)
        self.assertEqual(resp.context['selected_categories'], [])
        self.assertEqual(resp.context['related_categories'], [])

    def test_with_parent_category(self):
        resp = self.app.get("%s?category=%s" % (reverse("dataset-list"), self.category1.pk))
        self.assertEqual(list(resp.context['object_list']), [
            self.dataset1,
            self.dataset2,
            self.dataset3,
            self.dataset4
        ])
        self.assertEqual(resp.context['selected_categories'], [self.category1.pk])
        self.assertEqual(resp.context['related_categories'], [
            self.category1.pk,
            self.category2.pk,
            self.category3.pk,
            self.category4.pk
        ])

    def test_with_middle_category(self):
        resp = self.app.get("%s?category=%s" % (reverse("dataset-list"), self.category2.pk))
        self.assertEqual(list(resp.context['object_list']), [self.dataset2, self.dataset4])
        self.assertEqual(resp.context['selected_categories'], [self.category2.pk])
        self.assertEqual(resp.context['related_categories'], [
            self.category1.pk,
            self.category2.pk,
            self.category4.pk
        ])

    def test_with_child_category(self):
        resp = self.app.get("%s?category=%s" % (reverse("dataset-list"), self.category4.pk))
        self.assertEqual(list(resp.context['object_list']), [self.dataset4])
        self.assertEqual(resp.context['selected_categories'], [self.category4.pk])
        self.assertEqual(resp.context['related_categories'], [
            self.category1.pk,
            self.category2.pk,
            self.category4.pk
        ])

    def test_with_parent_and_child_category(self):
        resp = self.app.get("%s?category=%s&category=%s" % (reverse("dataset-list"),
                                                            self.category1.pk, self.category4.pk))
        self.assertEqual(list(resp.context['object_list']), [self.dataset4])
        self.assertEqual(resp.context['selected_categories'], [
            self.category1.pk,
            self.category4.pk
        ])
        self.assertEqual(resp.context['related_categories'], [
            self.category1.pk,
            self.category2.pk,
            self.category4.pk
        ])


class TagFilterTest(WebTest):
    def setUp(self):
        self.dataset1 = DatasetFactory(tags="tag1, tag2, tag3")
        self.dataset2 = DatasetFactory(tags="tag3, tag4, tag5, tag1")

    def test_without_query(self):
        resp = self.app.get(reverse('dataset-list'))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1, self.dataset2])
        self.assertEqual(resp.context['selected_tags'], [])
        self.assertEqual(resp.context['related_tags'], [])

    def test_with_one_tag(self):
        resp = self.app.get("%s?tags=tag2" % reverse("dataset-list"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1])
        self.assertEqual(resp.context['selected_tags'], ['tag2'])
        self.assertEqual(resp.context['related_tags'], ['tag1', 'tag2', 'tag3'])

    def test_with_shared_tag(self):
        resp = self.app.get("%s?tags=tag3" % reverse("dataset-list"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1, self.dataset2])
        self.assertEqual(resp.context['selected_tags'], ['tag3'])
        self.assertEqual(resp.context['related_tags'], ['tag1', 'tag2', 'tag3', 'tag4', 'tag5'])

    def test_with_multiple_tags(self):
        resp = self.app.get("%s?tags=tag4&tags=tag3" % reverse("dataset-list"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset2])
        self.assertEqual(resp.context['selected_tags'], ['tag4', 'tag3'])
        self.assertEqual(resp.context['related_tags'], ['tag1', 'tag3', 'tag4', 'tag5'])


class FrequencyFilterTest(WebTest):
    def setUp(self):
        self.frequency = FrequencyFactory()
        self.dataset1 = DatasetFactory(frequency=self.frequency)
        self.dataset2 = DatasetFactory(frequency=self.frequency)

    def test_without_query(self):
        resp = self.app.get(reverse('dataset-list'))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1, self.dataset2])
        self.assertIsNone(resp.context['selected_frequency'])

    def test_with_frequency(self):
        resp = self.app.get("%s?frequency=%s" % (reverse("dataset-list"),  self.frequency.pk))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1, self.dataset2])
        self.assertEqual(resp.context['selected_frequency'], self.frequency.pk)


class DateFilterTest(WebTest):
    def setUp(self):
        self.dataset1 = DatasetFactory(published=datetime(2022, 3, 1))
        self.dataset2 = DatasetFactory(published=datetime(2022, 2, 1))
        self.dataset3 = DatasetFactory(published=datetime(2021, 12, 1))

    def test_without_query(self):
        resp = self.app.get(reverse('dataset-list'))
        self.assertEqual(list(resp.context['object_list']), [
            self.dataset1,
            self.dataset2,
            self.dataset3
        ])
        self.assertIsNone(resp.context['selected_date_from'])
        self.assertIsNone(resp.context['selected_date_to'])

    def test_with_date_from(self):
        resp = self.app.get("%s?date_from=2022-02-10" % reverse("dataset-list"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset1])
        self.assertEqual(resp.context['selected_date_from'], "2022-02-10")
        self.assertIsNone(resp.context['selected_date_to'])

    def test_with_date_to(self):
        resp = self.app.get("%s?date_to=2022-02-10" % reverse("dataset-list"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset2, self.dataset3])
        self.assertIsNone(resp.context['selected_date_from'])
        self.assertEqual(resp.context['selected_date_to'], "2022-02-10")

    def test_with_dates_from_and_to(self):
        resp = self.app.get("%s?date_from=2022-01-01&date_to=2022-02-10" % reverse("dataset-list"))
        self.assertEqual(list(resp.context['object_list']), [self.dataset2])
        self.assertEqual(resp.context['selected_date_from'], "2022-01-01")
        self.assertEqual(resp.context['selected_date_to'], "2022-02-10")


class AllFilterTest(WebTest):
    def setUp(self):
        self.organization = OrganizationFactory()
        self.category = CategoryFactory()
        self.frequency = FrequencyFactory()
        self.dataset = DatasetFactory(
            status=Dataset.HAS_DATA,
            tags="tag1, tag2, tag3",
            published=datetime(2022, 2, 9),
            organization=self.organization,
            category=self.category,
            frequency=self.frequency
        )

    def test_dataset_filter_all(self):
        resp = self.app.get(reverse("dataset-list"), {
            'status': Dataset.HAS_DATA,
            'organization': self.organization.pk,
            'category': self.category.pk,
            'tags': ['tag1', 'tag2'],
            'frequency': self.frequency.pk,
            'date_from': '2022-01-01',
            'date_to': '2022-02-10',
        })

        self.assertEqual(list(resp.context['object_list']), [self.dataset])
        self.assertEqual(resp.context['selected_status'], Dataset.HAS_DATA)
        self.assertEqual(resp.context['selected_organization'], self.organization.pk)
        self.assertEqual(resp.context['selected_categories'], [self.category.pk])
        self.assertEqual(resp.context['related_categories'], [self.category.pk])
        self.assertEqual(resp.context['selected_tags'], ["tag1", "tag2"])
        self.assertEqual(resp.context['related_tags'], ["tag1", "tag2", "tag3"])
        self.assertEqual(resp.context['selected_frequency'], self.frequency.pk)
        self.assertEqual(resp.context['selected_date_from'], "2022-01-01")
        self.assertEqual(resp.context['selected_date_to'], "2022-02-10")


