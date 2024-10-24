import pytest
from django.contrib.contenttypes.models import ContentType
import factory

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action, pre_representative_delete
from vitrina.projects.factories import ProjectFactory
from vitrina.projects.models import Project
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
def test_organization_add_permission_non_superuser():
    user = UserFactory()
    res = has_perm(user, Action.CREATE, Organization)
    assert res is False


@pytest.mark.django_db
def test_organization_add_permission_superuser():
    user = UserFactory(is_superuser=True)
    res = has_perm(user, Action.CREATE, Organization)
    assert res is True


@pytest.mark.django_db
def test_has_perm__is_staff():
    user = UserFactory(is_staff=True)
    res = has_perm(user, Action.CREATE, Organization)
    assert res is True


@pytest.mark.django_db
def test_organization_edit_permission_manager():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.UPDATE, organization)
    assert res is False


@pytest.mark.django_db
def test_organization_edit_permission_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.UPDATE, organization)
    assert res is True


@pytest.mark.django_db
def test_dataset_create_permission_organization_manager():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.CREATE, Dataset, organization)
    assert res is True


@pytest.mark.django_db
def test_dataset_create_permission_organization_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, Dataset, organization)
    assert res is True


@pytest.mark.django_db
def test_dataset_edit_permission_organization_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.UPDATE, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_edit_permission_organization_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.UPDATE, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_edit_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.UPDATE, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_edit_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.UPDATE, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_history_view_permission_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.HISTORY_VIEW, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_history_view_permission_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.HISTORY_VIEW, dataset)
    assert res is True


@pytest.mark.django_db
def test_request_create_permission_authenticated():
    user = UserFactory()
    res = has_perm(user, Action.CREATE, Request)
    assert res is True


@pytest.mark.django_db
def test_request_edit_permission_non_author():
    user = UserFactory()
    request = RequestFactory()
    res = has_perm(user, Action.UPDATE, request)
    assert res is False


@pytest.mark.django_db
def test_request_edit_permission_author():
    user = UserFactory()
    request = RequestFactory(user=user)
    res = has_perm(user, Action.UPDATE, request)
    assert res is True


@pytest.mark.django_db
def test_project_create_permission_authenticated():
    user = UserFactory()
    res = has_perm(user, Action.CREATE, Project)
    assert res is True


@pytest.mark.django_db
def test_project_edit_permission_non_author():
    user = UserFactory()
    project = ProjectFactory()
    res = has_perm(user, Action.UPDATE, project)
    assert res is False


@pytest.mark.django_db
def test_project_edit_permission_author():
    user = UserFactory()
    project = ProjectFactory(user=user)
    res = has_perm(user, Action.UPDATE, project)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_create_permission_organization_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_create_permission_organization_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_create_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_create_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_edit_permission_organization_manager():
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset.organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset_distribution.dataset.organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.UPDATE, dataset_distribution)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_edit_permission_organization_coordinator():
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset_distribution.dataset.organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.UPDATE, dataset_distribution)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_edit_permission_dataset_manager():
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset_distribution.dataset.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.UPDATE, dataset_distribution)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_edit_permission_dataset_coordinator():
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset_distribution.dataset.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.UPDATE, dataset_distribution)
    assert res is True


@pytest.mark.django_db
def test_organization_representative_create_permission_manager():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.CREATE, Representative, organization)
    assert res is False


@pytest.mark.django_db
def test_organization_representative_create_permission_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, Representative, organization)
    assert res is True


@pytest.mark.django_db
def test_organization_representative_edit_permission_manager():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.UPDATE, manager)
    assert res is False


@pytest.mark.django_db
def test_organization_representative_edit_permission_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.UPDATE, coordinator)
    assert res is True


@pytest.mark.django_db
def test_organization_representative_view_permission_manager():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.VIEW, Representative, organization)
    assert res is False


@pytest.mark.django_db
def test_organization_representative_view_permission_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.VIEW, Representative, organization)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_create_permission_organization_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.CREATE, Representative, dataset)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_create_permission_organization_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, Representative, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_create_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.CREATE, Representative, dataset)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_create_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(manager.user, Action.CREATE, Representative, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_edit_permission_organization_manager():
    dataset = DatasetFactory()
    organization_ct = ContentType.objects.get_for_model(dataset.organization)
    dataset_ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=organization_ct,
        object_id=dataset.organization.pk,
        role=Representative.MANAGER
    )
    representative = RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk
    )
    res = has_perm(manager.user, Action.UPDATE, representative)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_edit_permission_organization_coordinator():
    dataset = DatasetFactory()
    organization_ct = ContentType.objects.get_for_model(dataset.organization)
    dataset_ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(
        content_type=organization_ct,
        object_id=dataset.organization.pk,
        role=Representative.COORDINATOR
    )
    representative = RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk
    )
    res = has_perm(coordinator.user, Action.UPDATE, representative)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_edit_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.MANAGER
    )
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk
    )
    res = has_perm(manager.user, Action.UPDATE, representative)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_edit_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR
    )
    representative = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk
    )
    res = has_perm(manager.user, Action.UPDATE, representative)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_view_permission_organization_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.VIEW, Representative, dataset)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_view_permission_organization_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.VIEW, Representative, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_view_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.VIEW, Representative, dataset)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_view_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.VIEW, Representative, dataset)
    assert res is True


@pytest.mark.django_db
def test_user_edit_permission_non_author():
    user = UserFactory()
    non_author = UserFactory()
    res = has_perm(non_author, Action.UPDATE, user)
    assert res is False


@pytest.mark.django_db
def test_user_edit_permission_author():
    user = UserFactory()
    res = has_perm(user, Action.UPDATE, user)
    assert res is True


@pytest.mark.django_db
def test_user_view_permission_non_author():
    user = UserFactory()
    non_author = UserFactory()
    res = has_perm(non_author, Action.VIEW, user)
    assert res is False


@pytest.mark.django_db
def test_user_view_permission_author():
    user = UserFactory()
    res = has_perm(user, Action.VIEW, user)
    assert res is True


@pytest.mark.django_db
def test_dataset_structure_create_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.CREATE, DatasetStructure, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_structure_create_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, DatasetStructure, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_structure_create_permission_organization_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.MANAGER
    )
    res = has_perm(manager.user, Action.CREATE, DatasetStructure, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_structure_create_permission_organization_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct,
        object_id=dataset.organization.pk,
        role=Representative.COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, DatasetStructure, dataset)
    assert res is True


@pytest.mark.django_db
def test_pre_representative_delete__one_organization():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=organization.pk
    )
    pre_representative_delete(rep)
    rep.refresh_from_db()
    assert rep.user.is_active is False


@pytest.mark.django_db
def test_pre_representative_delete__two_organizations():
    user = UserFactory()
    organization1 = OrganizationFactory()
    organization2 = OrganizationFactory()
    ct = ContentType.objects.get_for_model(Organization)
    rep = RepresentativeFactory(
        content_type=ct,
        object_id=organization1.pk,
        user=user
    )
    RepresentativeFactory(
        content_type=ct,
        object_id=organization2.pk,
        user=user
    )
    pre_representative_delete(rep)
    user.refresh_from_db()
    assert user.is_active is True


@pytest.mark.django_db
def test_pre_representative_delete__same_organization_dataset():
    user = UserFactory()
    organization = OrganizationFactory()
    dataset = DatasetFactory(organization=organization)
    org_ct = ContentType.objects.get_for_model(organization)
    dataset_ct = ContentType.objects.get_for_model(dataset)
    rep = RepresentativeFactory(
        content_type=org_ct,
        object_id=organization.pk,
        user=user
    )
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk,
        user=user
    )
    pre_representative_delete(rep)
    user.refresh_from_db()
    assert user.is_active is False


@pytest.mark.django_db
def test_pre_representative_delete__different_organization_dataset():
    user = UserFactory()
    organization = OrganizationFactory()
    dataset = DatasetFactory()
    org_ct = ContentType.objects.get_for_model(organization)
    dataset_ct = ContentType.objects.get_for_model(dataset)
    rep = RepresentativeFactory(
        content_type=org_ct,
        object_id=organization.pk,
        user=user
    )
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk,
        user=user
    )
    pre_representative_delete(rep)
    user.refresh_from_db()
    assert user.is_active is True
