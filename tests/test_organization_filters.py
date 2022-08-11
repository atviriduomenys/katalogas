import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.orgs.factories import OrganizationFactory


@pytest.mark.django_db
def test_dataset_filter_jurisdiction(app: DjangoTestApp):
    organization1 = OrganizationFactory(jurisdiction="Jurisdiction1")
    organization2 = OrganizationFactory(jurisdiction="Jurisdiction2")
    organization3 = OrganizationFactory(jurisdiction="Jurisdiction2")

    # without query
    resp = app.get(reverse('organization-list'))
    assert resp.status == '200 OK'
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

    # with jurisdiction
    resp = app.get("%s?jurisdiction=Jurisdiction1" % reverse('organization-list'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 1
    assert resp.context['object_list'][0].pk == organization1.pk
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

    # with another jurisdiction
    resp = app.get("%s?jurisdiction=Jurisdiction2" % reverse('organization-list'))
    assert resp.status == '200 OK'
    assert len(resp.context['object_list']) == 2
    assert resp.context['object_list'][0].pk == organization2.pk
    assert resp.context['object_list'][1].pk == organization3.pk
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

    # with jurisdiction that doesn't exist
    resp = app.get("%s?jurisdiction=doesnotexist" % reverse('organization-list'))
    assert resp.status == '200 OK'
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
