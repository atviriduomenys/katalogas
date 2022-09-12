import pytest
from datetime import datetime
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory


@pytest.fixture
def data_for_tabs():
    parent_organization = OrganizationFactory(slug="org1")
    organization = parent_organization.add_child(**OrganizationFactory.stub(slug="org2").__dict__)
    dataset = DatasetFactory(organization=organization)
    representative = RepresentativeFactory(organization=organization)
    return {
        'parent': parent_organization,
        'organization': organization,
        'dataset': dataset,
        'representative': representative
    }


@pytest.mark.django_db
def test_organization_detail_tab(app: DjangoTestApp, data_for_tabs):
    resp = app.get(reverse('organization-detail', args=[data_for_tabs["organization"].kind,
                                                        data_for_tabs["organization"].slug]))
    assert list(resp.context['ancestors']) == [data_for_tabs["parent"]]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Informacija"]


@pytest.mark.django_db
def test_organization_members_tab(app: DjangoTestApp, data_for_tabs):
    resp = app.get(reverse('organization-members', args=[data_for_tabs["organization"].kind,
                                                         data_for_tabs["organization"].slug]))
    assert list(resp.context['members']) == [data_for_tabs["representative"]]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Organizacijos nariai"]


@pytest.mark.django_db
def test_organization_dataset_tab(app: DjangoTestApp, data_for_tabs):
    resp = app.get(reverse('organization-datasets', args=[data_for_tabs["organization"].kind,
                                                          data_for_tabs["organization"].slug]))
    assert list(resp.context['object_list']) == [data_for_tabs["dataset"]]
    assert list(resp.html.find("li", class_="is-active").a.stripped_strings) == ["Duomenų rinkiniai"]


@pytest.fixture
def organizations():
    organization1 = OrganizationFactory(
        slug="org1",
        title="Organization 1",
        created=datetime(2022, 8, 22, 10, 30),
        jurisdiction="Jurisdiction1"
    )
    organization2 = OrganizationFactory(
        slug="org2",
        title="Organization 2",
        created=datetime(2022, 10, 22, 10, 30),
        jurisdiction="Jurisdiction2"
    )
    organization3 = OrganizationFactory(
        slug="org3",
        title="Organization 3",
        created=datetime(2022, 9, 22, 10, 30),
        jurisdiction="Jurisdiction2"
    )
    return [organization1, organization2, organization3]


@pytest.mark.django_db
def test_search_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2], organizations[0]]


@pytest.mark.django_db
def test_search_with_query_that_doesnt_match(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "doesnt-match"))
    assert len(resp.context['object_list']) == 0


@pytest.mark.django_db
def test_search_with_query_that_matches_one(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "1"))
    assert list(resp.context['object_list']) == [organizations[0]]


@pytest.mark.django_db
def test_search_with_query_that_matches_all(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=%s" % (reverse('organization-list'), "organization"))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2], organizations[0]]


@pytest.mark.django_db
def test_filter_without_query(app: DjangoTestApp, organizations):
    resp = app.get(reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2], organizations[0]]
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
def test_filter_with_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=Jurisdiction1" % reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[0]]
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
def test_filter_with_other_jurisdiction(app: DjangoTestApp, organizations):
    resp = app.get("%s?jurisdiction=Jurisdiction2" % reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[1], organizations[2]]
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
def test_filter_with_non_existent_jurisdiction(app: DjangoTestApp, organizations):
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
def test_filter_with_jurisdiction_and_title(app: DjangoTestApp, organizations):
    resp = app.get("%s?q=1&jurisdiction=Jurisdiction1" % reverse('organization-list'))
    assert list(resp.context['object_list']) == [organizations[0]]
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


@pytest.mark.django_db
def test_filter_with_query_containing_special_characters(app: DjangoTestApp):
    organization = OrganizationFactory(title="Organization \"<'>\\", jurisdiction="Jurisdiction\"<'>\\")
    resp = app.get("%s?q=\"<'>\\&jurisdiction=Jurisdiction\"<'>\\" % reverse('organization-list'))
    assert list(resp.context['object_list']) == [organization]
    assert resp.context['selected_jurisdiction'] == "Jurisdiction\"<'>\\"
    assert resp.context['jurisdictions'] == [
        {
            'title': "Jurisdiction\"<'>\\",
            'query': "?q=\"<'>\\&jurisdiction=Jurisdiction\"<'>\\",
            'count': 1
        },
    ]
