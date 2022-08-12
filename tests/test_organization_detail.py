import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory


@pytest.mark.django_db
def test_organization_detail_tab(app: DjangoTestApp):
    organization = OrganizationFactory()
    dataset = DatasetFactory(organization=organization)
    representative = RepresentativeFactory(organization=organization)

    resp = app.get(reverse('organization-detail', args=[organization.kind, organization.slug]))
    assert resp.status == '200 OK'
    assert len(resp.context['members']) == 1
    assert resp.context['members'][0].pk == representative.pk
    assert len(resp.context['datasets']) == 1
    assert resp.context['datasets'][0].pk == dataset.pk
    assert True is resp.context['detail_active']
    assert False is resp.context['members_active']
    assert False is resp.context['datasets_active']


@pytest.mark.django_db
def test_organization_members_tab(app: DjangoTestApp):
    organization = OrganizationFactory()
    dataset = DatasetFactory(organization=organization)
    representative = RepresentativeFactory(organization=organization)

    resp = app.get(reverse('organization-members', args=[organization.kind, organization.slug]))
    assert resp.status == '200 OK'
    assert len(resp.context['members']) == 1
    assert resp.context['members'][0].pk == representative.pk
    assert len(resp.context['datasets']) == 1
    assert resp.context['datasets'][0].pk == dataset.pk
    assert False is resp.context['detail_active']
    assert True is resp.context['members_active']
    assert False is resp.context['datasets_active']


@pytest.mark.django_db
def test_organization_dataset_tab(app: DjangoTestApp):
    organization = OrganizationFactory()
    dataset = DatasetFactory(organization=organization)
    representative = RepresentativeFactory(organization=organization)

    resp = app.get(reverse('organization-datasets', args=[organization.kind, organization.slug]))
    assert resp.status == '200 OK'
    assert len(resp.context['members']) == 1
    assert resp.context['members'][0].pk == representative.pk
    assert len(resp.context['datasets']) == 1
    assert resp.context['datasets'][0].pk == dataset.pk
    assert False is resp.context['detail_active']
    assert False is resp.context['members_active']
    assert True is resp.context['datasets_active']
