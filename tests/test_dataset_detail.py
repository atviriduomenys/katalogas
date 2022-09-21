import pytest
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory


@pytest.fixture
def dataset():
    dataset = DatasetFactory(status="HAS_DATA")
    return dataset


@pytest.mark.django_db
def test_dataset_detail_without_tags(app: DjangoTestApp, dataset):
    resp = app.get(dataset.get_absolute_url())
    assert resp.context['tags'] == []


@pytest.mark.django_db
def test_dataset_detail_tags(app: DjangoTestApp, dataset):
    dataset.tags = "tag-1, tag-2, tag-3"
    dataset.save()
    resp = app.get(dataset.get_absolute_url())
    assert resp.context['tags'] == ['tag-1', 'tag-2', 'tag-3']


@pytest.mark.django_db
def test_dataset_detail_status(app: DjangoTestApp, dataset):
    resp = app.get(dataset.get_absolute_url())
    assert resp.context['status'] == "Atvertas"

