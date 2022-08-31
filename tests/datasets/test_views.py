from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory


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
