import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.orgs.factories import OrganizationFactory


@pytest.fixture
def organizations():
    organization1 = OrganizationFactory(title="Organization 1", jurisdiction="Jurisdiction1")
    organization2 = OrganizationFactory(title="Organization 2", jurisdiction="Jurisdiction2")
    organization3 = OrganizationFactory(title="Organization 3", jurisdiction="Jurisdiction2")
    return [organization1, organization2, organization3]


@pytest.mark.django_db
def test_dataset_filter_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert len(resp.context['object_list']) == 3
    assert resp.context['selected_jurisdiction'] is None
    assert resp.context['jurisdictions'] == [
        {
            'title': 'Jurisdiction1',
            'query': "?jurisdiction=Jurisdiction1",
            'count': 1
        },
        {
            'title': 'Jurisdiction2',
            'query': "?jurisdiction=Jurisdiction2",
            'count': 2
        }
    ]


@pytest.mark.django_db
def test_dataset_filter_with_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=Jurisdiction1" % reverse('organization-list'))
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == organizations[0].pk
    assert resp.context['selected_jurisdiction'] == "Jurisdiction1"
    assert resp.context['jurisdictions'] == [
        {
            'title': 'Jurisdiction1',
            'query': "?jurisdiction=Jurisdiction1",
            'count': 1
        },
        {
            'title': 'Jurisdiction2',
            'query': "?jurisdiction=Jurisdiction2",
            'count': 0
        }
    ]


@pytest.mark.django_db
def test_dataset_filter_with_other_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=Jurisdiction2" % reverse('organization-list'))
    assert len(resp.context['object_list']) == 2
    assert resp.context['object_list'][0].pk == organizations[1].pk
    assert resp.context['object_list'][1].pk == organizations[2].pk
    assert resp.context['selected_jurisdiction'] == "Jurisdiction2"
    assert resp.context['jurisdictions'] == [
        {
            'title': 'Jurisdiction1',
            'query': "?jurisdiction=Jurisdiction1",
            'count': 0
        },
        {
            'title': 'Jurisdiction2',
            'query': "?jurisdiction=Jurisdiction2",
            'count': 2
        }
    ]


@pytest.mark.django_db
def test_dataset_filter_with_non_existent_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=doesnotexist" % reverse('organization-list'))
    assert len(resp.context['object_list']) == 0
    assert resp.context['selected_jurisdiction'] == "doesnotexist"
    assert resp.context['jurisdictions'] == [
        {
            'title': 'Jurisdiction1',
            'query': "?jurisdiction=Jurisdiction1",
            'count': 0
        },
        {
            'title': 'Jurisdiction2',
            'query': "?jurisdiction=Jurisdiction2",
            'count': 0
        }
    ]


@pytest.mark.django_db
def test_dataset_filter_with_jurisdiction_and_title(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=1&jurisdiction=Jurisdiction1" % reverse('organization-list'))
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == organizations[0].pk
    assert resp.context['selected_jurisdiction'] == "Jurisdiction1"
    assert resp.context['jurisdictions'] == [
        {
            'title': 'Jurisdiction1',
            'query': "?q=1&jurisdiction=Jurisdiction1",
            'count': 1
        },
        {
            'title': 'Jurisdiction2',
            'query': "?q=1&jurisdiction=Jurisdiction2",
            'count': 0
        }
    ]
