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
    assert len(resp.context['tags']) == 0


@pytest.mark.django_db
def test_dataset_detail_tags(app: DjangoTestApp, dataset):
    tag_str = "tag-1, tag-2, tag-3"
    dataset.tags = tag_str
    dataset.save()
    resp = app.get(dataset.get_absolute_url())
    assert len(resp.context['tags']) == 3
    assert str(resp.context['tags']) == tag_str


@pytest.mark.django_db
def test_dataset_detail_status(app: DjangoTestApp, dataset):
    resp = app.get(dataset.get_absolute_url())
    assert resp.context['status'] == "Atvertas"


@pytest.mark.django_db
def test_dataset_detail_other_context_data(app: DjangoTestApp, dataset):
    resp = app.get(dataset.get_absolute_url())

    # hardcoded values, will need to change with later tasks
    assert resp.context['subscription'] == []
    assert resp.context['rating'] == 3.0

