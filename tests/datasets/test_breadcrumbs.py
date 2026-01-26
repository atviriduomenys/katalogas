import pytest

from vitrina.datasets.factories import DatasetFactory, OrganizationFactory
from vitrina.datasets.views import DatasetDetailView, ResourceSubclassCreateView
from vitrina.datasets.mixins import Crumb


@pytest.mark.django_db
def test_dataset_detail_get_breadcrumbs_returns_dataset_chain():
    dataset = DatasetFactory()
    view = DatasetDetailView()
    view.object = dataset
    crumbs = view.get_breadcrumbs()
    assert all(isinstance(crumb, Crumb) for crumb in crumbs)
    titles = [crumb.title for crumb in crumbs]
    assert dataset.organization.title in titles
    assert titles[-1] == dataset.title
    assert crumbs[-1].is_current is True


@pytest.mark.django_db
def test_resource_subclass_create_org_breadcrumbs():
    org = OrganizationFactory()
    view = ResourceSubclassCreateView()
    view.kwargs = {"pk": org.pk}
    crumbs = view.get_breadcrumbs()
    titles = [crumb.title for crumb in crumbs]
    assert titles[:2] == ["Pradžia", org.title]
    assert "Duomenų ištekliai" in titles
    assert titles[-1] == "Pridėti duomenų išteklių"
    assert crumbs[-1].is_current is True


@pytest.mark.django_db
def test_resource_subclass_create_child_breadcrumbs():
    parent = DatasetFactory()
    view = ResourceSubclassCreateView()
    view.kwargs = {"pk": parent.organization_id, "parent_id": parent.pk}
    crumbs = view.get_breadcrumbs()
    titles = [crumb.title for crumb in crumbs]
    assert parent.title in titles
    assert titles[-1] in ["Pridėti vaikinį duomenų išteklių", "Pridėti duomenų išteklių"]
    assert crumbs[-1].is_current is True
