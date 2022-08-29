import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory


@pytest.fixture
def data_for_tabs():
    parent_organization = OrganizationFactory()
    organization = parent_organization.add_child(**OrganizationFactory.stub().__dict__)
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
