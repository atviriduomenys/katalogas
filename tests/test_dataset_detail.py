from datetime import datetime

import pytest
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory


@pytest.fixture
def dataset():
    org = OrganizationFactory(
        title="test organization",
        created=datetime(2022, 9, 22, 10, 30),
        jurisdiction="test_jurisdiction",
        kind='test_org_kind',
        slug='test_org_slug'
    )
    dataset = DatasetFactory(
        title="Testinis duomenų rinkinys",
        title_en="Test dataset",
        status="HAS_DATA",
        published=datetime(2022, 6, 1),
        organization=org,
        slug='test_dataset_slug'
    )
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


@pytest.mark.django_db
def test_dataset_detail_other_context_data(app: DjangoTestApp, dataset):
    resp = app.get(dataset.get_absolute_url())

    # hardcoded values, will need to change with later tasks
    assert resp.context['subscription'] == []
    assert resp.context['rating'] == 3.0

