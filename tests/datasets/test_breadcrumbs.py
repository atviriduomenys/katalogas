import pytest
from django.urls import reverse

from vitrina.datasets.factories import DatasetFactory, DCATResourceSubclassFactory, OrganizationFactory
from vitrina.datasets.views import DatasetDetailView, ResourceSubclassCreateView
from vitrina.datasets.mixins import Crumb

@pytest.mark.django_db
def test_dataset_detail_get_breadcrumbs_returns_dataset_chain():
    ds = DatasetFactory()
    v = DatasetDetailView()
    v.object = ds
    crumbs = v.get_breadcrumbs()
    assert all(isinstance(c, Crumb) for c in crumbs)
    titles = [c.title for c in crumbs]
    assert ds.organization.title in titles
    assert titles[-1] == ds.title
    assert crumbs[-1].is_current is True

@pytest.mark.django_db
def test_resource_subclass_create_org_breadcrumbs():
    org = OrganizationFactory()
    v = ResourceSubclassCreateView()
    v.kwargs = {"pk": org.pk}
    crumbs = v.get_breadcrumbs()
    titles = [c.title for c in crumbs]
    assert titles[:2] == ["Pradžia", org.title]
    assert "Duomenų ištekliai" in titles
    assert titles[-1] == "Pridėti duomenų išteklių"
    assert crumbs[-1].is_current is True

@pytest.mark.django_db
def test_resource_subclass_create_child_breadcrumbs():
    parent = DatasetFactory()
    v = ResourceSubclassCreateView()
    v.kwargs = {"pk": parent.organization_id, "parent_id": parent.pk}
    crumbs = v.get_breadcrumbs()
    titles = [c.title for c in crumbs]
    assert parent.title in titles
    assert titles[-1] in ["Pridėti vaikinį duomenų išteklių", "Pridėti duomenų išteklių"]
    assert crumbs[-1].is_current is True