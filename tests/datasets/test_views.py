from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp, WebTest
from factory.django import FileField

from vitrina.datasets.factories import DatasetFactory, DatasetStructureFactory
from vitrina.orgs.factories import OrganizationFactory


@pytest.fixture
def datasets():
    dataset1 = DatasetFactory(
        title="Duomenų rinkinys 1",
        title_en="Dataset 1",
        published=datetime(2022, 6, 1)
    )
    dataset2 = DatasetFactory(
        title="Duomenų rinkinys 2 \"<'>\\",
        title_en="Dataset 2",
        published=datetime(2022, 8, 1)
    )
    dataset3 = DatasetFactory(
        title="Duomenų rinkinys 3",
        title_en="Dataset 3",
        published=datetime(2022, 7, 1)
    )
    return [dataset1, dataset2, dataset3]


@pytest.mark.django_db
def test_search_without_query(app: DjangoTestApp, datasets):
    resp = app.get(reverse('dataset-list'))
    assert list(resp.context['object_list']) == [datasets[1], datasets[2], datasets[0]]


@pytest.mark.django_db
def test_search_with_query_that_doesnt_match(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "doesnt-match"))
    assert len(resp.context['object_list']) == 0


@pytest.mark.django_db
def test_search_with_query_that_matches_one(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "1"))
    assert list(resp.context['object_list']) == [datasets[0]]


@pytest.mark.django_db
def test_search_with_query_that_matches_all(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "rinkinys"))
    assert list(resp.context['object_list']) == [datasets[1], datasets[2], datasets[0]]


@pytest.mark.django_db
def test_search_with_query_that_matches_all_with_english_title(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "dataset"))
    assert list(resp.context['object_list']) == [datasets[1], datasets[2], datasets[0]]


@pytest.mark.django_db
def test_search_with_query_containing_special_characters(app: DjangoTestApp, datasets):
    resp = app.get("%s?q=%s" % (reverse('dataset-list'), "\"<'>\\"))
    assert list(resp.context['object_list']) == [datasets[1]]


@pytest.fixture
def dataset_structure_data():
    organization = OrganizationFactory(slug="org")
    dataset1 = DatasetFactory(slug="ds1", organization=organization)
    dataset2 = DatasetFactory(slug="ds2", organization=organization)
    dataset3 = DatasetFactory(slug="ds3", organization=organization)
    DatasetStructureFactory(dataset=dataset2)
    DatasetStructureFactory(dataset=dataset3, file=FileField(filename='file.csv', data=b'ab\0c'))
    return {
        'organization': organization,
        'dataset1': dataset1,
        'dataset2': dataset2,
        'dataset3': dataset3
    }


@pytest.mark.django_db
def test_without_structure(app: DjangoTestApp, dataset_structure_data):
    resp = app.get(reverse('dataset-structure', kwargs={
        'organization_kind': dataset_structure_data["organization"].kind,
        'organization_slug': dataset_structure_data["organization"].slug,
        'dataset_slug': dataset_structure_data["dataset1"].slug
    }), expect_errors=True)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_with_structure(app: DjangoTestApp, dataset_structure_data):
    resp = app.get(reverse('dataset-structure', kwargs={
        'organization_kind': dataset_structure_data["organization"].kind,
        'organization_slug': dataset_structure_data["organization"].slug,
        'dataset_slug': dataset_structure_data["dataset2"].slug
    }))
    assert resp.context['can_show'] is True
    assert list(resp.context['structure_data']) == [["Column"], ["Value"]]


@pytest.mark.django_db
def test_with_non_readable_structure(app: DjangoTestApp, dataset_structure_data):
    resp = app.get(reverse('dataset-structure', kwargs={
        'organization_kind': dataset_structure_data["organization"].kind,
        'organization_slug': dataset_structure_data["organization"].slug,
        'dataset_slug': dataset_structure_data["dataset3"].slug
    }))
    assert resp.context['can_show'] is False
    assert resp.context['structure_data'] == []
