from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp, WebTest
from factory.django import FileField

from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.orgs.factories import OrganizationFactory


@pytest.fixture
def datasets():
    dataset1 = DatasetFactory(title="Duomenų rinkinys 1", title_en="Dataset 1", published=datetime(2022, 6, 1))
    dataset2 = DatasetFactory(title="Duomenų rinkinys 2 \"<'>\\", title_en="Dataset 2", published=datetime(2022, 8, 1))
    dataset3 = DatasetFactory(title="Duomenų rinkinys 3", title_en="Dataset 3", published=datetime(2022, 7, 1))
    return [dataset1, dataset2, dataset3]


@pytest.mark.django_db
def test_without_query(app: DjangoTestApp, datasets):
    resp = app.get(reverse('dataset-list'))
    assert list(resp.context['object_list']) == [datasets[1], datasets[2], datasets[0]]


@pytest.mark.django_db
def test_with_query_that_doesnt_match(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "doesnt-match"))
    assert len(resp.context['object_list']) == 0


@pytest.mark.django_db
def test_with_query_that_matches_one(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "1"))
    assert list(resp.context['object_list']) == [datasets[0]]


@pytest.mark.django_db
def test_with_query_that_matches_all(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "rinkinys"))
    assert list(resp.context['object_list']) == [datasets[1], datasets[2], datasets[0]]


@pytest.mark.django_db
def test_with_query_that_matches_all_with_english_title(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "dataset"))
    assert list(resp.context['object_list']) == [datasets[1], datasets[2], datasets[0]]


@pytest.mark.django_db
def test_with_query_containing_special_characters(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "\"<'>\\"))
    assert list(resp.context['object_list']) == [datasets[1]]


class DatasetStructureTest(WebTest):
    def setUp(self):
        self.organization = OrganizationFactory(slug="org")
        self.dataset1 = DatasetFactory(slug="ds1", organization=self.organization)
        self.dataset2 = DatasetFactory(slug="ds2", organization=self.organization)
        self.dataset3 = DatasetFactory(slug="ds3", organization=self.organization)
        self.structure1 = DatasetStructureFactory(dataset=self.dataset2)
        self.structure2 = DatasetStructureFactory(
            dataset=self.dataset3,
            file=FileField(filename='file.csv', data=b'ab\0c')
        )

    def test_without_structure(self):
        resp = self.app.get(reverse('dataset-structure', kwargs={
            'organization_kind': self.organization.kind,
            'organization_slug': self.organization.slug,
            'dataset_slug': self.dataset1.slug
        }), expect_errors=True)
        self.assertEqual(resp.status_code, 404)

    def test_with_structure(self):
        resp = self.app.get(reverse('dataset-structure', kwargs={
            'organization_kind': self.organization.kind,
            'organization_slug': self.organization.slug,
            'dataset_slug': self.dataset2.slug
        }))
        self.assertEqual(resp.context['can_show'], True)
        self.assertEqual(list(resp.context['structure_data']), [["Column"], ["Value"]])

    def test_with_non_readable_structure(self):
        resp = self.app.get(reverse('dataset-structure', kwargs={
            'organization_kind': self.organization.kind,
            'organization_slug': self.organization.slug,
            'dataset_slug': self.dataset3.slug
        }))
        self.assertEqual(resp.context['can_show'], False)
        self.assertEqual(resp.context['structure_data'], [])
