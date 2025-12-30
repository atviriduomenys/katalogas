import pytest
from django.contrib.contenttypes.models import ContentType
import factory

from vitrina.datasets.factories import DatasetFactory, DCATResourceSubclassFactory
from vitrina.datasets.models import Dataset, DatasetStructure, DCATResourceSubclass
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action, pre_representative_delete, _has_dataset_perm, WRITE_ACTIONS
from vitrina.projects.factories import ProjectFactory
from vitrina.projects.models import Project
from vitrina.requests.factories import RequestFactory
from vitrina.requests.models import Request
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.users.factories import UserFactory


@pytest.fixture
def public_dataset():
    return DatasetFactory(is_public=True, access_rights=Dataset.PUBLIC)


@pytest.fixture
def non_public_dataset():
    return DatasetFactory(is_public=False, access_rights=Dataset.NON_PUBLIC)


@pytest.fixture
def confidential_dataset():
    return DatasetFactory(is_public=True, access_rights=Dataset.CONFIDENTIAL)


@pytest.fixture
def non_public_but_public_access_dataset():
    return DatasetFactory(is_public=False, access_rights=Dataset.PUBLIC)


@pytest.fixture
def representative_on_dataset(public_dataset):
    ct = ContentType.objects.get_for_model(public_dataset)
    return RepresentativeFactory(content_type=ct, object_id=public_dataset.pk, role=Representative.COORDINATOR)


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
    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.UPDATE, organization)
    assert res is False


@pytest.mark.django_db
def test_organization_edit_permission_open_data_representative():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.UPDATE, organization)
    assert res is False


@pytest.mark.django_db
def test_organization_edit_permission_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.RESOURCE_COORDINATOR)
    res = has_perm(coordinator.user, Action.UPDATE, organization)
    assert res is True


@pytest.mark.django_db
def test_dataset_create_permission_organization_manager():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.RESOURCE_MANAGER)
    res = has_perm(manager.user, Action.CREATE, Dataset, organization)
    assert res is True


@pytest.mark.django_db
def test_dataset_create_permission_organization_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.RESOURCE_COORDINATOR)
    res = has_perm(coordinator.user, Action.CREATE, Dataset, organization)
    assert res is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,can_write,action,dataset_fixture,expected",
    [
        ("global_manager", None, Action.CREATE, "public_dataset", True),
        ("global_manager", None, Action.UPDATE, "public_dataset", True),
        ("global_manager", None, Action.DELETE, "public_dataset", True),
        ("global_manager", None, Action.COMMENT, "public_dataset", True),
        ("global_manager", None, Action.STRUCTURE, "public_dataset", True),
        ("global_manager", None, Action.VIEW, "public_dataset", True),
        ("global_manager", None, Action.HISTORY_VIEW, "public_dataset", True),
        ("global_manager", None, Action.CREATE, "non_public_dataset", True),
        ("global_manager", None, Action.UPDATE, "non_public_dataset", True),
        ("global_manager", None, Action.VIEW, "confidential_dataset", True),
        ("global_manager", None, Action.DELETE, "non_public_but_public_access_dataset", True),
        ("resource_coordinator", True, Action.UPDATE, "confidential_dataset", True),
        ("resource_coordinator", False, Action.UPDATE, "confidential_dataset", False),
        ("resource_coordinator", None, Action.VIEW, "public_dataset", True),
        ("resource_coordinator", None, Action.VIEW, "non_public_dataset", True),
        ("resource_coordinator", None, Action.CREATE, "public_dataset", True),
        ("resource_manager", True, Action.UPDATE, "confidential_dataset", True),
        ("resource_manager", False, Action.UPDATE, "confidential_dataset", False),
        ("resource_manager", None, Action.VIEW, "public_dataset", True),
        ("authenticated", None, Action.VIEW, "public_dataset", True),
        ("authenticated", None, Action.VIEW, "non_public_dataset", False),
        ("authenticated", None, Action.VIEW, "confidential_dataset", False),
        ("authenticated", None, Action.UPDATE, "public_dataset", False),
        ("authenticated", None, Action.CREATE, "public_dataset", False),
    ],
)
def test_dataset_permissions(role, can_write, action, dataset_fixture, expected, request):
    dataset = request.getfixturevalue(dataset_fixture)
    user = UserFactory(is_staff=(role == "global_manager"))
    ct = ContentType.objects.get_for_model(dataset)
    rep_role = {"open_data_coordinator": Representative.OPEN_DATA_COORDINATOR, "open_data_manager": Representative.OPEN_DATA_MANAGER, "resource_coordinator": Representative.RESOURCE_COORDINATOR, "resource_manager": Representative.RESOURCE_MANAGER}
    RepresentativeFactory(
        content_type=ct, object_id=dataset.pk, role=rep_role, user=user
    )

    assert has_perm(user, action, dataset) is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,action,obj_fixture,expected",
    [
        ("coordinator", Action.UPDATE, "representative_on_dataset", True),
        ("resource_manager", Action.UPDATE, "representative_on_dataset", False),
        ("global_manager", Action.UPDATE, "representative_on_dataset", True),
        ("authenticated", Action.UPDATE, "representative_on_dataset", False),
    ],
)
def test_representative_update_permissions_fixed(role, action, obj_fixture, expected, request):
    obj = request.getfixturevalue(obj_fixture)
    dataset = Dataset.objects.get(pk=obj.object_id) if obj.content_type.model_class() == Dataset else None
    user = UserFactory(is_staff=(role == "global_manager"))
    if role == "coordinator" and dataset is not None:
        ct = ContentType.objects.get_for_model(dataset)
        RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_COORDINATOR,
            user=user,
        )
    assert has_perm(user, action, obj) is expected


@pytest.mark.django_db
def test_dataset_history_view_permission_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.HISTORY_VIEW, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_history_view_permission_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_COORDINATOR)
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
    res = has_perm(user, Action.REQUEST_UPDATE, request)
    assert res is False


@pytest.mark.django_db
def test_request_edit_permission_author():
    user = UserFactory()
    request = RequestFactory(user=user)
    res = has_perm(user, Action.REQUEST_UPDATE, request)
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
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_create_permission_organization_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_create_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_create_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_COORDINATOR)
    res = has_perm(coordinator.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_edit_permission_organization_manager():
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset.organization)
    manager = RepresentativeFactory(
        content_type=ct, object_id=dataset_distribution.dataset.organization.pk, role=Representative.OPEN_DATA_MANAGER
    )
    res = has_perm(manager.user, Action.UPDATE, dataset_distribution)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_edit_permission_organization_coordinator():
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct, object_id=dataset_distribution.dataset.organization.pk, role=Representative.OPEN_DATA_COORDINATOR
    )
    res = has_perm(coordinator.user, Action.UPDATE, dataset_distribution)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_edit_permission_dataset_manager():
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset)
    manager = RepresentativeFactory(
        content_type=ct, object_id=dataset_distribution.dataset.pk, role=Representative.OPEN_DATA_MANAGER
    )
    res = has_perm(manager.user, Action.UPDATE, dataset_distribution)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_edit_permission_dataset_coordinator():
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset)
    coordinator = RepresentativeFactory(
        content_type=ct, object_id=dataset_distribution.dataset.pk, role=Representative.OPEN_DATA_COORDINATOR
    )
    res = has_perm(coordinator.user, Action.UPDATE, dataset_distribution)
    assert res is True


@pytest.mark.django_db
def test_organization_representative_create_permission_manager():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.CREATE, Representative, organization)
    assert res is False


@pytest.mark.django_db
def test_organization_representative_create_permission_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_COORDINATOR)
    res = has_perm(coordinator.user, Action.CREATE, Representative, organization)
    assert res is True


@pytest.mark.django_db
def test_organization_representative_edit_permission_manager():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.UPDATE, manager)
    assert res is False


@pytest.mark.django_db
def test_organization_representative_edit_permission_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_COORDINATOR)
    res = has_perm(coordinator.user, Action.UPDATE, coordinator)
    assert res is True


@pytest.mark.django_db
def test_organization_representative_view_permission_manager():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.VIEW, Representative, organization)
    assert res is False


@pytest.mark.django_db
def test_organization_representative_view_permission_coordinator():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=Representative.OPEN_DATA_COORDINATOR)
    res = has_perm(coordinator.user, Action.VIEW, Representative, organization)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_create_permission_organization_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.CREATE, Representative, dataset)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_create_permission_organization_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, Representative, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_create_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.CREATE, Representative, dataset)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_create_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_COORDINATOR)
    res = has_perm(manager.user, Action.CREATE, Representative, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_edit_permission_organization_manager():
    dataset = DatasetFactory()
    organization_ct = ContentType.objects.get_for_model(dataset.organization)
    dataset_ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(
        content_type=organization_ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_MANAGER
    )
    representative = RepresentativeFactory(content_type=dataset_ct, object_id=dataset.pk)
    res = has_perm(manager.user, Action.UPDATE, representative)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_edit_permission_organization_coordinator():
    dataset = DatasetFactory()
    organization_ct = ContentType.objects.get_for_model(dataset.organization)
    dataset_ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(
        content_type=organization_ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_COORDINATOR
    )
    representative = RepresentativeFactory(content_type=dataset_ct, object_id=dataset.pk)
    res = has_perm(coordinator.user, Action.UPDATE, representative)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_edit_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER)
    representative = RepresentativeFactory(content_type=ct, object_id=dataset.pk)
    res = has_perm(manager.user, Action.UPDATE, representative)
    assert res is False


@pytest.mark.django_db
def test_dataset_representative_edit_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_COORDINATOR)
    representative = RepresentativeFactory(content_type=ct, object_id=dataset.pk)
    res = has_perm(manager.user, Action.UPDATE, representative)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_view_permission_organization_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.VIEW, Representative, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_view_permission_organization_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_COORDINATOR
    )
    res = has_perm(coordinator.user, Action.VIEW, Representative, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_view_permission_dataset_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.VIEW, Representative, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_representative_view_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_COORDINATOR)
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
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.CREATE, DatasetStructure, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_structure_create_permission_dataset_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_COORDINATOR)
    res = has_perm(coordinator.user, Action.CREATE, DatasetStructure, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_structure_create_permission_organization_manager():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_MANAGER)
    res = has_perm(manager.user, Action.CREATE, DatasetStructure, dataset)
    assert res is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_right,expected",
    [
        (Dataset.PUBLIC, True),
        (Dataset.RESTRICTED, True),
        (Dataset.NON_PUBLIC, False),
        (Dataset.CONFIDENTIAL, False),
    ]
)
def test_dataset_structure_create_permission_open_data_representative(access_right, expected):
    org = DatasetFactory().organization
    ct = ContentType.objects.get_for_model(org)

    manager = RepresentativeFactory(
        content_type=ct,
        object_id=org.pk,
        role=Representative.OPEN_DATA_MANAGER,
    )

    dataset = DatasetFactory(organization=org, access_rights=access_right)

    result = has_perm(manager.user, Action.UPDATE, DatasetStructure, dataset)

    assert result == expected


@pytest.mark.django_db
def test_dataset_structure_create_permission_organization_coordinator():
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct, object_id=dataset.organization.pk, role=Representative.OPEN_DATA_COORDINATOR
    )
    res = has_perm(coordinator.user, Action.CREATE, DatasetStructure, dataset)
    assert res is True


@pytest.mark.django_db
def test_pre_representative_delete__one_organization():
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    rep = RepresentativeFactory(content_type=ct, object_id=organization.pk)
    pre_representative_delete(rep)
    rep.refresh_from_db()
    assert rep.user.is_active is False


@pytest.mark.django_db
def test_pre_representative_delete__two_organizations():
    user = UserFactory()
    organization1 = OrganizationFactory()
    organization2 = OrganizationFactory()
    ct = ContentType.objects.get_for_model(Organization)
    rep = RepresentativeFactory(content_type=ct, object_id=organization1.pk, user=user)
    RepresentativeFactory(content_type=ct, object_id=organization2.pk, user=user)
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
    rep = RepresentativeFactory(content_type=org_ct, object_id=organization.pk, user=user)
    RepresentativeFactory(content_type=dataset_ct, object_id=dataset.pk, user=user)
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
    rep = RepresentativeFactory(content_type=org_ct, object_id=organization.pk, user=user)
    RepresentativeFactory(content_type=dataset_ct, object_id=dataset.pk, user=user)
    pre_representative_delete(rep)
    user.refresh_from_db()
    assert user.is_active is True


@pytest.mark.django_db
def test_dataset_create_permission_dataset_publisher():
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=None,
        role=Representative.OPEN_DATA_MANAGER,
    )

    res = has_perm(user, Action.CREATE, Dataset, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_create_permission_organization_publisher():
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=dataset.organization.pk,
        user=None,
        role=Representative.OPEN_DATA_MANAGER,
    )

    res = has_perm(user, Action.CREATE, Dataset, dataset.organization)
    assert res is True


@pytest.mark.django_db
def test_dataset_edit_permission_dataset_publisher():
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=Representative.RESOURCE_MANAGER,
    )

    res = has_perm(user, Action.UPDATE, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_edit_permission_organization_publisher():
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=dataset.organization.pk,
        user=user,
        role=Representative.RESOURCE_MANAGER,
    )

    res = has_perm(user, Action.UPDATE, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_edit_permission_organization_open_data_representative_non_public():
    dataset = DatasetFactory(is_public=False)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=dataset.organization.pk,
        user=user,
        role=Representative.OPEN_DATA_MANAGER,
    )

    res = has_perm(user, Action.UPDATE, dataset)
    assert res is False


@pytest.mark.django_db
def test_dataset_history_view_permission_publisher():
    organization = OrganizationFactory()
    user = UserFactory()
    user.organization = organization
    user.save()

    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        organization=organization, content_type=ct, object_id=dataset.pk, role=Representative.OPEN_DATA_MANAGER, user=None
    )
    res = has_perm(user, Action.HISTORY_VIEW, dataset)
    assert res is True


@pytest.mark.django_db
def test_organization_representative_view_permission_publisher():
    user_organization = OrganizationFactory()
    user = UserFactory()
    user.organization = user_organization
    user.save()

    organization = OrganizationFactory()

    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(
        organization=user_organization,
        content_type=ct,
        object_id=organization.pk,
        role=Representative.OPEN_DATA_MANAGER,
        user=None,
    )
    res = has_perm(user, Action.VIEW, Representative, organization)
    assert res is False


@pytest.mark.django_db
def test_organization_create_publisher():
    organization = OrganizationFactory()
    user = UserFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=organization.pk,
        user=None,
        role=Representative.OPEN_DATA_MANAGER,
    )

    res = has_perm(user, Action.CREATE, Organization)
    assert res is False


@pytest.mark.django_db
def test_organization_edit_publisher():
    organization = OrganizationFactory()
    user = UserFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=organization.pk,
        user=None,
        role=Representative.OPEN_DATA_MANAGER,
    )

    res = has_perm(user, Action.UPDATE, organization)
    assert res is False


@pytest.mark.django_db
def test_dataset_distribution_create_permission_organization_publisher():
    dataset = DatasetFactory()
    organization = OrganizationFactory()
    user = UserFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset.organization),
        object_id=dataset.organization.pk,
        user=None,
        role=Representative.OPEN_DATA_MANAGER,
    )
    res = has_perm(user, Action.CREATE, DatasetDistribution, dataset)
    assert res is True


@pytest.mark.django_db
def test_dataset_distribution_edit_permission_organization_publisher():
    organization = OrganizationFactory()
    user = UserFactory()
    user.organization = organization
    user.save()

    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset.organization)
    RepresentativeFactory(
        organization=organization,
        content_type=ct,
        object_id=dataset_distribution.dataset.organization.pk,
        role=Representative.RESOURCE_MANAGER,
        user=user,
    )
    res = has_perm(user, Action.UPDATE, dataset_distribution)
    assert res is True


class TestHasDatasetPerm:
    @pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED])
    def test_permissions_with_dataset_open_data_representative(self, access_rights: str):
        dataset = DatasetFactory(access_rights=access_rights)
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_MANAGER
        )

        assert _has_dataset_perm(representative.user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
    def test_permissions_with_dataset_resource_representative(self, access_rights: str):
        dataset = DatasetFactory(access_rights=access_rights)
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.RESOURCE_MANAGER
        )

        assert _has_dataset_perm(representative.user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED])
    def test_permissions_with_organization_open_data_representative(self, access_rights: str):
        organization = OrganizationFactory()
        dataset = DatasetFactory(access_rights=access_rights, organization=organization)
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=Representative.OPEN_DATA_MANAGER
        )

        assert _has_dataset_perm(representative.user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
    def test_permissions_with_organization_resource_representative(self, access_rights: str):
        organization = OrganizationFactory()
        dataset = DatasetFactory(access_rights=access_rights, organization=organization)
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=Representative.RESOURCE_MANAGER
        )

        assert _has_dataset_perm(representative.user, Action.UPDATE, dataset, dataset) is True


    def test_permission_with_organization_representative_for_all_related_datasets(self):
        parent_organization = OrganizationFactory()
        parent_dataset = DatasetFactory(organization=parent_organization)
        child_organization = OrganizationFactory()
        child_dataset = DatasetFactory(organization=child_organization)

        child_dataset.move(parent_dataset, "sorted-child")
        child_dataset.refresh_from_db()
        parent_dataset.refresh_from_db()
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(parent_organization),
            object_id=parent_organization.pk,
        )

        assert _has_dataset_perm(representative.user, Action.UPDATE, child_dataset, child_dataset)

