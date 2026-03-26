import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied

from vitrina.api.mixins import DatasetAccessMixin
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from django_webtest import DjangoTestApp

from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory


@pytest.mark.parametrize(
    "representative_role", [Representative.OPEN_DATA_MANAGER, Representative.OPEN_DATA_COORDINATOR]
)
@pytest.mark.django_db
def test_is_open_data_representative_user_is_none_with_open_data_role(
    app: DjangoTestApp, representative_role: Representative
):
    org = OrganizationFactory()
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = representative_role
    assert view.is_open_data_representative() is True


@pytest.mark.parametrize(
    "role,expected",
    [
        (Representative.RESOURCE_COORDINATOR, False),
        (Representative.RESOURCE_MANAGER, False),
        (Representative.OPEN_DATA_COORDINATOR, True),
        (Representative.OPEN_DATA_MANAGER, True),
    ],
)
@pytest.mark.django_db
def test_is_open_data_representative_with_user(app: DjangoTestApp, role: Representative, expected: bool):
    org = OrganizationFactory()
    user = UserFactory()
    ct = ContentType.objects.get_for_model(org)
    RepresentativeFactory(user=user, content_type=ct, object_id=org.pk, role=role)
    view = DatasetAccessMixin()
    view.user = user
    view.organization = org
    view.organization_role = None
    assert view.is_open_data_representative() is expected


@pytest.mark.django_db
def test_is_open_data_representative_with_non_representative_user(app: DjangoTestApp):
    org = OrganizationFactory()
    user = UserFactory()
    view = DatasetAccessMixin()
    view.user = user
    view.organization = org
    view.organization_role = None
    assert view.is_open_data_representative() is False


@pytest.mark.parametrize(
    "access_rights,expected_count",
    [
        (Dataset.PUBLIC, 1),
        (Dataset.RESTRICTED, 1),
        (Dataset.NON_PUBLIC, 0),
        (Dataset.CONFIDENTIAL, 0),
    ],
)
@pytest.mark.django_db
def test_filter_queryset_by_access_with_user(app: DjangoTestApp, access_rights: str, expected_count: int):
    org = OrganizationFactory()
    user = UserFactory()
    DatasetFactory(organization=org, access_rights=access_rights)
    view = DatasetAccessMixin()
    view.user = user
    view.organization = org
    view.organization_role = None
    queryset = Dataset.objects.filter(organization=org)
    result = view._filter_queryset_by_access(queryset)
    assert result.count() == expected_count


@pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED])
@pytest.mark.django_db
def test_check_dataset_access_passes_for_user_with_access(app: DjangoTestApp, access_rights: str):
    org = OrganizationFactory()
    user = UserFactory()
    dataset = DatasetFactory(organization=org, access_rights=access_rights)
    view = DatasetAccessMixin()
    view.user = user
    view.organization = org
    view.organization_role = None
    view._check_dataset_access(dataset)


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_check_dataset_access_raises_for_user_without_access(app: DjangoTestApp, access_rights: str):
    org = OrganizationFactory()
    user = UserFactory()
    dataset = DatasetFactory(organization=org, access_rights=access_rights)
    view = DatasetAccessMixin()
    view.user = user
    view.organization = org
    view.organization_role = None
    with pytest.raises(PermissionDenied):
        view._check_dataset_access(dataset)


@pytest.mark.django_db
def test_is_open_data_representative_user_is_none_no_role(app: DjangoTestApp):
    org = OrganizationFactory()
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = None
    assert view.is_open_data_representative() is False


@pytest.mark.parametrize(
    "representative_role",
    [Representative.RESOURCE_COORDINATOR, Representative.RESOURCE_MANAGER],
)
@pytest.mark.django_db
def test_is_open_data_representative_user_is_none_with_resource_role(app: DjangoTestApp, representative_role: str):
    org = OrganizationFactory()
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = representative_role
    assert view.is_open_data_representative() is False


@pytest.mark.parametrize(
    "access_rights,expected_count",
    [
        (Dataset.PUBLIC, 1),
        (Dataset.RESTRICTED, 1),
        (Dataset.NON_PUBLIC, 0),
        (Dataset.CONFIDENTIAL, 0),
    ],
)
@pytest.mark.django_db
def test_filter_queryset_by_access_with_open_data_role(app: DjangoTestApp, access_rights: str, expected_count: int):
    org = OrganizationFactory()
    DatasetFactory(organization=org, access_rights=access_rights)
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = Representative.OPEN_DATA_MANAGER
    queryset = Dataset.objects.filter(organization=org)
    result = view._filter_queryset_by_access(queryset)
    assert result.count() == expected_count


@pytest.mark.parametrize(
    "access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL]
)
@pytest.mark.django_db
def test_filter_queryset_by_access_with_resource_role(app: DjangoTestApp, access_rights: str):
    org = OrganizationFactory()
    DatasetFactory(organization=org, access_rights=access_rights)
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = Representative.RESOURCE_MANAGER
    queryset = Dataset.objects.filter(organization=org)
    result = view._filter_queryset_by_access(queryset)
    assert result.count() == 1


@pytest.mark.django_db
def test_filter_queryset_by_access_no_user_no_role_returns_none(app: DjangoTestApp):
    org = OrganizationFactory()
    DatasetFactory(organization=org)
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = None
    queryset = Dataset.objects.filter(organization=org)
    result = view._filter_queryset_by_access(queryset)
    assert result.count() == 0


@pytest.mark.parametrize("access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED])
@pytest.mark.django_db
def test_check_dataset_access_passes_for_open_data_role(app: DjangoTestApp, access_rights: str):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org, access_rights=access_rights)
    assert dataset.access_rights == access_rights  # does this fail?
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = Representative.OPEN_DATA_MANAGER
    view._check_dataset_access(dataset)


@pytest.mark.parametrize("access_rights", [Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL])
@pytest.mark.django_db
def test_check_dataset_access_raises_for_open_data_role(app: DjangoTestApp, access_rights: str):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org, access_rights=access_rights)
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = Representative.OPEN_DATA_MANAGER
    with pytest.raises(PermissionDenied):
        view._check_dataset_access(dataset)


@pytest.mark.parametrize(
    "access_rights", [Dataset.PUBLIC, Dataset.RESTRICTED, Dataset.NON_PUBLIC, Dataset.CONFIDENTIAL]
)
@pytest.mark.django_db
def test_check_dataset_access_for_resource_role(app: DjangoTestApp, access_rights: str):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org, access_rights=access_rights)
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = Representative.RESOURCE_MANAGER
    view._check_dataset_access(dataset)


@pytest.mark.django_db
def test_check_dataset_access_raises_with_no_user_no_role(app: DjangoTestApp):
    org = OrganizationFactory()
    dataset = DatasetFactory(organization=org, access_rights=Dataset.PUBLIC)
    view = DatasetAccessMixin()
    view.user = None
    view.organization = org
    view.organization_role = None
    with pytest.raises(PermissionDenied):
        view._check_dataset_access(dataset)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "organization_role, is_information_system, expected",
    [
        (next(iter(Representative.OPEN_DATA_ROLE_KEYS)), True, False),
        (next(iter(Representative.OPEN_DATA_ROLE_KEYS)), False, False),
        (next(iter(Representative.RESOURCE_ROLE_KEYS)), True, False),
        (None, True, False),
    ],
)
def test_is_restricted_information_system(
    organization_role: str | None,
    is_information_system: bool,
    expected: bool,
) -> None:
    dataset = DatasetFactory(subclass__is_information_system=is_information_system)
    view = DatasetAccessMixin()
    view.organization_role = organization_role
    view.user = None
    assert view._is_restricted_information_system(dataset) is expected
