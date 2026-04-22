import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization, Representative
from vitrina.orgs.services import has_perm, Action, pre_representative_delete, _has_dataset_perm
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
    return RepresentativeFactory(
        content_type=ct, object_id=public_dataset.pk, role=Representative.OPEN_DATA_COORDINATOR
    )


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
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.OPEN_DATA_MANAGER, False),
        (Representative.RESOURCE_MANAGER, False),
    ],
)
def test_organization_edit_permission_managers(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)

    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)

    res = has_perm(manager.user, Action.UPDATE, organization)

    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_organization_edit_permission_coordinator(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)
    res = has_perm(coordinator.user, Action.UPDATE, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_create_permission_organization_manager(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)
    res = has_perm(manager.user, Action.CREATE, Dataset, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_create_permission_via_org_representative(role: str, expected: bool):
    organization = OrganizationFactory()

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=organization.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.CREATE, Dataset, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_create_permission_organization_coordinator(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)
    res = has_perm(coordinator.user, Action.CREATE, Dataset, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,action,dataset_fixture,expected",
    [
        ("global_manager", Action.CREATE, "public_dataset", True),
        ("global_manager", Action.UPDATE, "public_dataset", True),
        ("global_manager", Action.DELETE, "public_dataset", True),
        ("global_manager", Action.COMMENT, "public_dataset", True),
        ("global_manager", Action.STRUCTURE, "public_dataset", True),
        ("global_manager", Action.VIEW, "public_dataset", True),
        ("global_manager", Action.HISTORY_VIEW, "public_dataset", True),
        ("global_manager", Action.CREATE, "non_public_dataset", True),
        ("global_manager", Action.UPDATE, "non_public_dataset", True),
        ("global_manager", Action.VIEW, "confidential_dataset", True),
        ("global_manager", Action.DELETE, "non_public_but_public_access_dataset", True),
        ("resource_manager", Action.CREATE, "public_dataset", True),
        ("resource_manager", Action.CREATE, "non_public_dataset", True),
        ("resource_manager", Action.CREATE, "confidential_dataset", True),
        ("resource_manager", Action.UPDATE, "public_dataset", True),
        ("resource_manager", Action.UPDATE, "non_public_dataset", True),
        ("resource_manager", Action.UPDATE, "confidential_dataset", True),
        ("resource_manager", Action.VIEW, "public_dataset", True),
        ("resource_manager", Action.VIEW, "non_public_dataset", True),
        ("resource_manager", Action.VIEW, "confidential_dataset", True),
        ("resource_manager", Action.DELETE, "public_dataset", True),
        ("resource_manager", Action.DELETE, "non_public_dataset", True),
        ("resource_manager", Action.DELETE, "confidential_dataset", True),
        ("open_data_manager", Action.CREATE, "public_dataset", True),
        ("open_data_manager", Action.CREATE, "non_public_dataset", True),
        ("open_data_manager", Action.CREATE, "confidential_dataset", True),
        ("open_data_manager", Action.UPDATE, "public_dataset", True),
        ("open_data_manager", Action.UPDATE, "non_public_dataset", False),
        ("open_data_manager", Action.UPDATE, "confidential_dataset", False),
        ("open_data_manager", Action.VIEW, "public_dataset", True),
        ("open_data_manager", Action.VIEW, "non_public_dataset", False),
        ("open_data_manager", Action.VIEW, "confidential_dataset", False),
        ("open_data_manager", Action.DELETE, "public_dataset", True),
        ("open_data_manager", Action.DELETE, "non_public_dataset", False),
        ("open_data_manager", Action.DELETE, "confidential_dataset", False),
        ("authenticated", Action.VIEW, "public_dataset", True),
        ("authenticated", Action.VIEW, "non_public_dataset", False),
        ("authenticated", Action.VIEW, "confidential_dataset", False),
        ("authenticated", Action.UPDATE, "public_dataset", False),
        ("authenticated", Action.CREATE, "public_dataset", False),
    ],
)
def test_dataset_permissions(role, action, dataset_fixture, expected, request):
    dataset = request.getfixturevalue(dataset_fixture)
    user = UserFactory(is_staff=(role == "global_manager"))
    ct = ContentType.objects.get_for_model(dataset)
    rep_roles = {
        "open_data_manager": Representative.OPEN_DATA_MANAGER,
        "resource_manager": Representative.RESOURCE_MANAGER,
    }
    if role in rep_roles:
        RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=rep_roles[role],
            user=user,
        )

    assert has_perm(user, action, dataset) is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,action,dataset_fixture,expected",
    [
        ("resource_manager", Action.CREATE, "public_dataset", True),
        ("resource_manager", Action.CREATE, "non_public_dataset", True),
        ("resource_manager", Action.CREATE, "confidential_dataset", True),
        ("resource_manager", Action.UPDATE, "public_dataset", True),
        ("resource_manager", Action.UPDATE, "non_public_dataset", True),
        ("resource_manager", Action.UPDATE, "confidential_dataset", True),
        ("resource_manager", Action.VIEW, "public_dataset", True),
        ("resource_manager", Action.VIEW, "non_public_dataset", True),
        ("resource_manager", Action.VIEW, "confidential_dataset", True),
        ("resource_manager", Action.DELETE, "public_dataset", True),
        ("resource_manager", Action.DELETE, "non_public_dataset", True),
        ("resource_manager", Action.DELETE, "confidential_dataset", True),
        ("open_data_manager", Action.CREATE, "public_dataset", True),
        ("open_data_manager", Action.CREATE, "non_public_dataset", True),
        ("open_data_manager", Action.CREATE, "confidential_dataset", True),
        ("open_data_manager", Action.UPDATE, "public_dataset", True),
        ("open_data_manager", Action.UPDATE, "non_public_dataset", False),
        ("open_data_manager", Action.UPDATE, "confidential_dataset", False),
        ("open_data_manager", Action.VIEW, "public_dataset", True),
        ("open_data_manager", Action.VIEW, "non_public_dataset", False),
        ("open_data_manager", Action.VIEW, "confidential_dataset", False),
        ("open_data_manager", Action.DELETE, "public_dataset", True),
        ("open_data_manager", Action.DELETE, "non_public_dataset", False),
        ("open_data_manager", Action.DELETE, "confidential_dataset", False),
    ],
)
def test_dataset_permissions_via_org_representative(
    role: str, action: Action, dataset_fixture: str, expected: bool, request: pytest.FixtureRequest
):
    dataset = request.getfixturevalue(dataset_fixture)

    rep_roles = {
        "open_data_manager": Representative.OPEN_DATA_MANAGER,
        "resource_manager": Representative.RESOURCE_MANAGER,
    }

    representative_org = OrganizationFactory()
    dataset_ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk,
        role=rep_roles[role],
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=rep_roles[role],
        user=user,
        organization=None,
    )

    assert has_perm(user, action, dataset) is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,action,obj_fixture,expected",
    [
        ("resource_coordinator", Action.UPDATE, "representative_on_dataset", True),
        ("open_data_coordinator", Action.UPDATE, "representative_on_dataset", True),
        ("resource_manager", Action.UPDATE, "representative_on_dataset", False),
        ("open_data_manager", Action.UPDATE, "representative_on_dataset", False),
        ("global_manager", Action.UPDATE, "representative_on_dataset", True),
        ("authenticated", Action.UPDATE, "representative_on_dataset", False),
    ],
)
def test_representative_update_permissions_fixed(role, action, obj_fixture, expected, request):
    obj = request.getfixturevalue(obj_fixture)
    dataset = Dataset.objects.get(pk=obj.object_id) if obj.content_type.model_class() == Dataset else None
    user = UserFactory(is_staff=(role == "global_manager"))
    if (role in Representative.MANAGER_ROLES or role in Representative.COORDINATOR_ROLES) and dataset is not None:
        ct = ContentType.objects.get_for_model(dataset)
        RepresentativeFactory(
            content_type=ct,
            object_id=dataset.pk,
            role=role,
            user=user,
        )
    assert has_perm(user, action, obj) is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_history_view_permission_manager(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(manager.user, Action.HISTORY_VIEW, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_history_view_permission_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory()

    representative_org = OrganizationFactory()
    dataset_ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.HISTORY_VIEW, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_history_view_permission_coordinator(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(coordinator.user, Action.HISTORY_VIEW, dataset)
    assert res is expected


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
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_distribution_create_permission_organization_manager(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=role)
    res = has_perm(manager.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_distribution_create_permission_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory()

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(dataset.organization)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=dataset.organization.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.CREATE, DatasetDistribution, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_distribution_create_permission_organization_coordinator(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=role)
    res = has_perm(coordinator.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_distribution_create_permission_dataset_manager(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(manager.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_distribution_create_permission_dataset_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory()

    representative_org = OrganizationFactory()
    dataset_ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.CREATE, DatasetDistribution, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_distribution_create_permission_dataset_coordinator(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(coordinator.user, Action.CREATE, DatasetDistribution, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_distribution_edit_permission_organization_manager(role: str, expected: bool):
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset.organization)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset_distribution.dataset.organization.pk, role=role)
    res = has_perm(manager.user, Action.UPDATE, dataset_distribution)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_distribution_edit_permission_via_org_representative(role: str, expected: bool):
    dataset_distribution = DatasetDistributionFactory()

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(dataset_distribution.dataset.organization)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=dataset_distribution.dataset.organization.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.UPDATE, dataset_distribution)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_distribution_edit_permission_organization_coordinator(role: str, expected: bool):
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset.organization)
    coordinator = RepresentativeFactory(
        content_type=ct, object_id=dataset_distribution.dataset.organization.pk, role=role
    )
    res = has_perm(coordinator.user, Action.UPDATE, dataset_distribution)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_distribution_edit_permission_dataset_manager(role: str, expected: bool):
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset_distribution.dataset.pk, role=role)
    res = has_perm(manager.user, Action.UPDATE, dataset_distribution)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_distribution_edit_permission_dataset_via_org_representative(role: str, expected: bool):
    dataset_distribution = DatasetDistributionFactory()

    representative_org = OrganizationFactory()
    dataset_ct = ContentType.objects.get_for_model(dataset_distribution.dataset)
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset_distribution.dataset.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.UPDATE, dataset_distribution)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_distribution_edit_permission_dataset_coordinator(role: str, expected: bool):
    dataset_distribution = DatasetDistributionFactory()
    ct = ContentType.objects.get_for_model(dataset_distribution.dataset)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset_distribution.dataset.pk, role=role)
    res = has_perm(coordinator.user, Action.UPDATE, dataset_distribution)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_organization_representative_create_permission_manager(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)
    res = has_perm(manager.user, Action.CREATE, Representative, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_organization_representative_create_permission_via_org_representative(role: str, expected: bool):
    organization = OrganizationFactory()

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=organization.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.CREATE, Representative, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_organization_representative_create_permission_representative(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)
    res = has_perm(representative.user, Action.CREATE, Representative, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_organization_representative_edit_permission_representative(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)
    res = has_perm(representative.user, Action.UPDATE, Representative, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_organization_representative_edit_permission_via_org_representative(role: str, expected: bool):
    organization = OrganizationFactory()

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=organization.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    assert has_perm(user, Action.UPDATE, Representative, organization) is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_organization_representative_view_permission_manager(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    manager = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)
    res = has_perm(manager.user, Action.VIEW, Representative, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_organization_representative_view_permission_via_org_representative(role: str, expected: bool):
    organization = OrganizationFactory()

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=organization.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.VIEW, Representative, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_organization_representative_view_permission_coordinator(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)
    res = has_perm(coordinator.user, Action.VIEW, Representative, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_representative_create_permission_organization_manager(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=role)
    res = has_perm(manager.user, Action.CREATE, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_representative_create_permission_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory()

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(dataset.organization)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=dataset.organization.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.CREATE, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_representative_create_permission_organization_coordinator(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=role)
    res = has_perm(coordinator.user, Action.CREATE, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_representative_create_permission_dataset_manager(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(manager.user, Action.CREATE, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_representative_create_permission_dataset_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory()

    representative_org = OrganizationFactory()
    dataset_ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.CREATE, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_representative_create_permission_dataset_coordinator(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(manager.user, Action.CREATE, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_representative_edit_permission_organization_manager(role: str, expected: bool):
    dataset = DatasetFactory()
    organization_ct = ContentType.objects.get_for_model(dataset.organization)
    dataset_ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=organization_ct, object_id=dataset.organization.pk, role=role)
    representative = RepresentativeFactory(content_type=dataset_ct, object_id=dataset.pk)
    res = has_perm(manager.user, Action.UPDATE, representative)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_representative_edit_permission_organization_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory()

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(dataset.organization)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=dataset.organization.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    dataset_ct = ContentType.objects.get_for_model(dataset)
    representative = RepresentativeFactory(content_type=dataset_ct, object_id=dataset.pk)

    res = has_perm(user, Action.UPDATE, representative)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_representative_edit_permission_organization_coordinator(role: str, expected: bool):
    dataset = DatasetFactory()
    organization_ct = ContentType.objects.get_for_model(dataset.organization)
    dataset_ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(content_type=organization_ct, object_id=dataset.organization.pk, role=role)
    representative = RepresentativeFactory(content_type=dataset_ct, object_id=dataset.pk)
    res = has_perm(coordinator.user, Action.UPDATE, representative)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_representative_edit_permission_dataset_manager(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    representative = RepresentativeFactory(content_type=ct, object_id=dataset.pk)
    res = has_perm(manager.user, Action.UPDATE, representative)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_representative_edit_permission_dataset_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory()

    representative_org = OrganizationFactory()
    dataset_ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    representative = RepresentativeFactory(content_type=dataset_ct, object_id=dataset.pk)

    res = has_perm(user, Action.UPDATE, representative)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_representative_edit_permission_dataset_coordinator(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    representative = RepresentativeFactory(content_type=ct, object_id=dataset.pk)
    res = has_perm(manager.user, Action.UPDATE, representative)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_representative_view_permission_organization_manager(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=role)
    res = has_perm(manager.user, Action.VIEW, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_representative_view_permission_organization_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory()

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(dataset.organization)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=dataset.organization.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.VIEW, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_representative_view_permission_organization_coordinator(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=role)
    res = has_perm(coordinator.user, Action.VIEW, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_representative_view_permission_dataset_manager(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(manager.user, Action.VIEW, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_representative_view_permission_dataset_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory()

    representative_org = OrganizationFactory()
    dataset_ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.VIEW, Representative, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.OPEN_DATA_COORDINATOR, True),
    ],
)
def test_dataset_representative_view_permission_dataset_coordinator(role: str, expected: bool):
    dataset = DatasetFactory()
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(coordinator.user, Action.VIEW, Representative, dataset)
    assert res is expected


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
@pytest.mark.parametrize(
    "access_rights, role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_structure_create_permission_dataset_manager(access_rights: str, role: str, expected: bool):
    dataset = DatasetFactory(access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(manager.user, Action.CREATE, DatasetStructure, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights, role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_structure_create_permission_dataset_via_org_representative(
    access_rights: str, role: str, expected: bool
):
    dataset = DatasetFactory(access_rights=access_rights)

    representative_org = OrganizationFactory()
    dataset_ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        content_type=dataset_ct,
        object_id=dataset.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.CREATE, DatasetStructure, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_COORDINATOR, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_COORDINATOR, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_COORDINATOR, True),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_COORDINATOR, True),
        (Dataset.PUBLIC, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_COORDINATOR, True),
    ],
)
def test_dataset_structure_create_permission_dataset_coordinator(access_rights: str, role: str, expected: bool):
    dataset = DatasetFactory(access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(coordinator.user, Action.CREATE, DatasetStructure, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_structure_create_permission_organization_manager(access_rights: str, role: str, expected: bool):
    dataset = DatasetFactory(access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    manager = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=role)
    res = has_perm(manager.user, Action.CREATE, DatasetStructure, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_structure_update_permission_manager(access_rights: str, role: str, expected: bool):
    org = DatasetFactory().organization
    ct = ContentType.objects.get_for_model(org)

    manager = RepresentativeFactory(
        content_type=ct,
        object_id=org.pk,
        role=role,
    )

    dataset = DatasetFactory(organization=org, access_rights=access_rights)

    result = has_perm(manager.user, Action.UPDATE, DatasetStructure, dataset)

    assert result == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_structure_update_permission_via_org_representative(access_rights: str, role: str, expected: bool):
    org = DatasetFactory().organization

    representative_org = OrganizationFactory()
    org_ct = ContentType.objects.get_for_model(org)
    RepresentativeFactory(
        content_type=org_ct,
        object_id=org.pk,
        role=role,
        organization=representative_org,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(representative_org)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=representative_org.pk,
        role=role,
        user=user,
        organization=None,
    )

    dataset = DatasetFactory(organization=org, access_rights=access_rights)

    result = has_perm(user, Action.UPDATE, DatasetStructure, dataset)

    assert result == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_COORDINATOR, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_COORDINATOR, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_COORDINATOR, True),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_COORDINATOR, True),
        (Dataset.PUBLIC, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_COORDINATOR, True),
    ],
)
def test_dataset_structure_create_permission_organization_coordinator(access_rights: str, role: str, expected: bool):
    dataset = DatasetFactory(access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset.organization)
    coordinator = RepresentativeFactory(content_type=ct, object_id=dataset.organization.pk, role=role)
    res = has_perm(coordinator.user, Action.CREATE, DatasetStructure, dataset)
    assert res is expected


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
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_create_permission_dataset_publisher(role: str, expected: bool):
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
        role=role,
    )

    res = has_perm(user, Action.CREATE, Dataset, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_create_permission_dataset_publisher_via_org_representative(role: str, expected: bool):
    dataset = DatasetFactory(is_public=False)

    organization = OrganizationFactory()
    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=None,
        role=role,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=organization.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.CREATE, Dataset, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
def test_dataset_create_permission_organization_publisher(role: str, expected: bool):
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
        role=role,
    )

    res = has_perm(user, Action.CREATE, Dataset, dataset.organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_edit_permission_dataset_publisher(access_rights: str, role: str, expected: bool):
    dataset = DatasetFactory(is_public=False, access_rights=access_rights)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
        role=role,
    )

    res = has_perm(user, Action.UPDATE, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_edit_permission_dataset_publisher_via_org_representative(
    access_rights: str, role: str, expected: bool
):
    dataset = DatasetFactory(is_public=False, access_rights=access_rights)

    organization = OrganizationFactory()
    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=None,
        role=role,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=organization.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.UPDATE, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_edit_permission_organization_publisher(access_rights: str, role: str, expected: bool):
    dataset = DatasetFactory(is_public=False, access_rights=access_rights)
    user = UserFactory()
    organization = OrganizationFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(organization),
        object_id=dataset.organization.pk,
        user=user,
        role=role,
    )

    res = has_perm(user, Action.UPDATE, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_history_view_permission_publisher(access_rights: str, role: str, expected: bool):
    organization = OrganizationFactory()
    user = UserFactory()
    user.organization = organization
    user.save()

    dataset = DatasetFactory(access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(organization=organization, content_type=ct, object_id=dataset.pk, role=role, user=user)
    res = has_perm(user, Action.HISTORY_VIEW, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, False),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_history_view_permission_publisher_via_org_representative(
    access_rights: str, role: str, expected: bool
):
    organization = OrganizationFactory()
    dataset = DatasetFactory(access_rights=access_rights)

    ct = ContentType.objects.get_for_model(dataset)
    RepresentativeFactory(
        organization=organization,
        content_type=ct,
        object_id=dataset.pk,
        role=role,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=organization.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.HISTORY_VIEW, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.OPEN_DATA_MANAGER, False),
        (Representative.RESOURCE_MANAGER, False),
    ],
)
def test_organization_representative_view_permission_publisher(role: str, expected: bool):
    user_organization = OrganizationFactory()
    user = UserFactory()
    user.organization = user_organization
    user.save()

    organization = OrganizationFactory()

    ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        organization=user_organization,
        content_type=ct,
        object_id=organization.pk,
        role=role,
        user=None,
    )
    res = has_perm(user, Action.VIEW, Representative, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.OPEN_DATA_MANAGER, False),
        (Representative.RESOURCE_MANAGER, False),
    ],
)
def test_organization_representative_view_permission_publisher_via_org_representative(role: str, expected: bool):
    user_organization = OrganizationFactory()
    organization = OrganizationFactory()

    org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        organization=user_organization,
        content_type=org_ct,
        object_id=organization.pk,
        role=role,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(user_organization)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=user_organization.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.VIEW, Representative, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.OPEN_DATA_MANAGER, False),
        (Representative.RESOURCE_MANAGER, False),
    ],
)
def test_organization_create_publisher(role: str, expected: bool):
    organization = OrganizationFactory()
    user = UserFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=organization.pk,
        user=None,
        role=role,
    )

    res = has_perm(user, Action.CREATE, Organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.OPEN_DATA_MANAGER, False),
        (Representative.RESOURCE_MANAGER, False),
    ],
)
def test_organization_edit_publisher(role: str, expected: bool):
    organization = OrganizationFactory()
    user = UserFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=organization.pk,
        user=None,
        role=role,
    )

    res = has_perm(user, Action.UPDATE, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.OPEN_DATA_MANAGER, False),
        (Representative.RESOURCE_MANAGER, False),
    ],
)
def test_organization_edit_publisher_via_org_representative(role: str, expected: bool):
    organization = OrganizationFactory()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(Organization),
        object_id=organization.pk,
        user=None,
        role=role,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=organization.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.UPDATE, organization)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.RESTRICTED, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.OPEN_DATA_MANAGER, True),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_distribution_create_permission_organization_publisher(access_rights: str, role: str, expected: bool):
    dataset = DatasetFactory(access_rights=access_rights)
    organization = OrganizationFactory()
    user = UserFactory()
    user.organization = organization
    user.save()

    RepresentativeFactory(
        organization=organization,
        content_type=ContentType.objects.get_for_model(dataset.organization),
        object_id=dataset.organization.pk,
        user=None,
        role=role,
    )
    res = has_perm(user, Action.CREATE, DatasetDistribution, dataset)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.OPEN_DATA_MANAGER, True),
        (Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_distribution_edit_permission_organization_publisher(role: str, expected: bool):
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
        role=role,
        user=user,
    )
    res = has_perm(user, Action.UPDATE, dataset_distribution)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.OPEN_DATA_MANAGER, True),
        (Representative.RESOURCE_MANAGER, True),
    ],
)
def test_dataset_distribution_edit_permission_organization_publisher_via_org_representative(role: str, expected: bool):
    organization = OrganizationFactory()
    dataset_distribution = DatasetDistributionFactory()

    ct = ContentType.objects.get_for_model(dataset_distribution.dataset.organization)
    RepresentativeFactory(
        organization=organization,
        content_type=ct,
        object_id=dataset_distribution.dataset.organization.pk,
        role=role,
        user=None,
    )

    user = UserFactory()
    rep_org_ct = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(
        content_type=rep_org_ct,
        object_id=organization.pk,
        role=role,
        user=user,
        organization=None,
    )

    res = has_perm(user, Action.UPDATE, dataset_distribution)
    assert res is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.RESOURCE_MANAGER, True),
        (Representative.OPEN_DATA_COORDINATOR, False),
        (Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_create_wizard_permission_organization(role: str, expected: bool):
    organization = OrganizationFactory()
    ct = ContentType.objects.get_for_model(organization)
    representative = RepresentativeFactory(content_type=ct, object_id=organization.pk, role=role)
    res = has_perm(representative.user, Action.CREATE_WIZARD, Dataset, organization)
    assert res is expected


@pytest.mark.django_db
def test_dataset_create_wizard_permission_global_manager():
    organization = OrganizationFactory()
    user = UserFactory(is_staff=True)
    res = has_perm(user, Action.CREATE_WIZARD, Dataset, organization)
    assert res is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "access_rights,role,expected",
    [
        (Dataset.PUBLIC, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_COORDINATOR, True),
        (Dataset.PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.RESTRICTED, Representative.RESOURCE_MANAGER, True),
        (Dataset.NON_PUBLIC, Representative.RESOURCE_MANAGER, True),
        (Dataset.CONFIDENTIAL, Representative.RESOURCE_MANAGER, True),
        (Dataset.PUBLIC, Representative.OPEN_DATA_COORDINATOR, False),
        (Dataset.PUBLIC, Representative.OPEN_DATA_MANAGER, False),
    ],
)
def test_dataset_update_wizard_permission_non_public_dataset(access_rights: str, role: str, expected: bool):
    dataset = DatasetFactory(is_public=False, access_rights=access_rights)
    ct = ContentType.objects.get_for_model(dataset)
    rep = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(rep.user, Action.UPDATE_WIZARD, dataset)
    assert res is expected


@pytest.mark.django_db
def test_dataset_update_wizard_permission_global_manager():
    dataset = DatasetFactory(is_public=False)
    user = UserFactory(is_staff=True)
    res = has_perm(user, Action.UPDATE_WIZARD, dataset)
    assert res is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "role",
    [
        Representative.RESOURCE_COORDINATOR,
        Representative.RESOURCE_MANAGER,
        Representative.OPEN_DATA_COORDINATOR,
        Representative.OPEN_DATA_MANAGER,
    ],
)
def test_dataset_update_wizard_not_allowed_for_public_is(role: str):
    # UPDATE_WIZARD has no ACL entry for is_public=True datasets
    dataset = DatasetFactory(is_public=True, access_rights=Dataset.PUBLIC)
    ct = ContentType.objects.get_for_model(dataset)
    rep = RepresentativeFactory(content_type=ct, object_id=dataset.pk, role=role)
    res = has_perm(rep.user, Action.UPDATE_WIZARD, dataset)
    assert res is False


class TestHasDatasetPerm:
    @pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED])
    def test_permissions_with_dataset_open_data_representative(self, access_rights: str):
        dataset = DatasetFactory(access_rights=access_rights)
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert _has_dataset_perm(representative.user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED])
    def test_permissions_with_dataset_open_data_via_org_representative(self, access_rights: str):
        dataset = DatasetFactory(access_rights=access_rights)

        representative_org = OrganizationFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        rep_org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=rep_org_ct,
            object_id=representative_org.pk,
            role=Representative.OPEN_DATA_MANAGER,
            user=user,
            organization=None,
        )

        assert _has_dataset_perm(user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize(
        "access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL]
    )
    def test_permissions_with_dataset_resource_representative(self, access_rights: str):
        dataset = DatasetFactory(access_rights=access_rights)
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.RESOURCE_MANAGER,
        )

        assert _has_dataset_perm(representative.user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize(
        "access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL]
    )
    def test_permissions_with_dataset_resource_via_org_representative(self, access_rights: str):
        dataset = DatasetFactory(access_rights=access_rights)

        representative_org = OrganizationFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        rep_org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=rep_org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert _has_dataset_perm(user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED])
    def test_permissions_with_organization_open_data_representative(self, access_rights: str):
        organization = OrganizationFactory()
        dataset = DatasetFactory(access_rights=access_rights, organization=organization)
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert _has_dataset_perm(representative.user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED])
    def test_permissions_with_organization_open_data_via_org_representative(self, access_rights: str):
        organization = OrganizationFactory()
        dataset = DatasetFactory(access_rights=access_rights, organization=organization)

        representative_org = OrganizationFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=Representative.OPEN_DATA_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        rep_org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=rep_org_ct,
            object_id=representative_org.pk,
            role=Representative.OPEN_DATA_MANAGER,
            user=user,
            organization=None,
        )

        assert _has_dataset_perm(user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize(
        "access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL]
    )
    def test_permissions_with_organization_resource_representative(self, access_rights: str):
        organization = OrganizationFactory()
        dataset = DatasetFactory(access_rights=access_rights, organization=organization)
        representative = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=Representative.RESOURCE_MANAGER,
        )

        assert _has_dataset_perm(representative.user, Action.UPDATE, dataset, dataset) is True

    @pytest.mark.parametrize(
        "access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL]
    )
    def test_permissions_with_organization_resource_via_org_representative(self, access_rights: str):
        organization = OrganizationFactory()
        dataset = DatasetFactory(access_rights=access_rights, organization=organization)

        representative_org = OrganizationFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        rep_org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=rep_org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert _has_dataset_perm(user, Action.UPDATE, dataset, dataset) is True

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


@pytest.mark.django_db
class TestViispOrganizationPermissions:
    def test_superuser_bypasses_viisp_check_organization_update(self):
        organization = OrganizationFactory()
        other_org = OrganizationFactory()
        superuser = UserFactory(is_superuser=True, is_viisp_login=True, viisp_company_code=other_org.company_code)

        res = has_perm(superuser, Action.UPDATE, organization)
        assert res is True

    def test_staff_bypasses_viisp_check_organization_update(self):
        organization = OrganizationFactory()
        other_org = OrganizationFactory()
        staff_user = UserFactory(is_staff=True, is_viisp_login=True, viisp_company_code=other_org.company_code)

        res = has_perm(staff_user, Action.UPDATE, organization)
        assert res is True

    def test_coordinator_with_matching_viisp_org_can_update(self):
        organization = OrganizationFactory()
        user = UserFactory(organization=organization, is_viisp_login=True, viisp_company_code=organization.company_code)
        ct = ContentType.objects.get_for_model(organization)
        RepresentativeFactory(
            organization=organization,
            content_type=ct,
            object_id=organization.pk,
            user=None,
        )

        res = has_perm(user, Action.UPDATE, organization)
        assert res is True

    def test_coordinator_with_mismatched_viisp_org_cannot_update(self):
        organization = OrganizationFactory()
        other_org = OrganizationFactory()
        user = UserFactory(organization=organization, is_viisp_login=True, viisp_company_code=other_org.company_code)
        ct = ContentType.objects.get_for_model(organization)
        RepresentativeFactory(
            organization=organization,
            content_type=ct,
            object_id=organization.pk,
            user=None,
        )

        res = has_perm(user, Action.UPDATE, organization)
        assert res is False

    def test_coordinator_without_viisp_org_cannot_update(self):
        organization = OrganizationFactory()
        user = UserFactory(
            organization=organization,
            is_viisp_login=False,  # This makes viisp_organization None
        )
        ct = ContentType.objects.get_for_model(organization)
        RepresentativeFactory(
            organization=organization,
            content_type=ct,
            object_id=organization.pk,
            user=None,
        )

        res = has_perm(user, Action.UPDATE, organization)
        assert res is False

    def test_direct_representative_bypasses_viisp_check(self):
        organization = OrganizationFactory()
        other_org = OrganizationFactory()
        ct = ContentType.objects.get_for_model(organization)
        coordinator = RepresentativeFactory(
            content_type=ct,
            object_id=organization.pk,
        )
        coordinator.user.is_viisp_login = True
        coordinator.user.viisp_company_code = other_org.company_code
        coordinator.user.save()

        res = has_perm(coordinator.user, Action.UPDATE, organization)
        assert res is True

    def test_viisp_check_for_representative_update_with_org_parent(self):
        organization = OrganizationFactory()
        user = UserFactory(organization=organization, is_viisp_login=True, viisp_company_code=organization.company_code)
        ct = ContentType.objects.get_for_model(organization)
        RepresentativeFactory(
            organization=organization,
            content_type=ct,
            object_id=organization.pk,
            user=None,
        )

        res = has_perm(user, Action.UPDATE, Representative, organization)
        assert res is True

    def test_viisp_check_fails_for_representative_update_mismatched_org(self):
        organization = OrganizationFactory()
        other_org = OrganizationFactory()
        user = UserFactory(organization=organization, is_viisp_login=True, viisp_company_code=other_org.company_code)
        ct = ContentType.objects.get_for_model(organization)
        RepresentativeFactory(
            organization=organization,
            content_type=ct,
            object_id=organization.pk,
            user=None,
        )

        res = has_perm(user, Action.UPDATE, Representative, organization)
        assert res is False

    def test_viisp_check_not_applied_to_dataset_create(self):
        organization = OrganizationFactory()
        other_org = OrganizationFactory()
        user = UserFactory(organization=organization, is_viisp_login=True, viisp_company_code=other_org.company_code)
        ct = ContentType.objects.get_for_model(organization)
        RepresentativeFactory(
            organization=organization,
            content_type=ct,
            object_id=organization.pk,
            user=None,
            role=Representative.OPEN_DATA_MANAGER,
        )

        res = has_perm(user, Action.CREATE, Dataset, organization)
        assert res is True
