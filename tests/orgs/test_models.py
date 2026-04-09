import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target_role, expected",
    [
        (Representative.OPEN_DATA_COORDINATOR, True),
        (Representative.OPEN_DATA_MANAGER, True),
        (Representative.RESOURCE_COORDINATOR, False),
        (Representative.RESOURCE_MANAGER, False),
    ],
)
def test_open_data_coordinator_can_be_updated_by(target_role, expected):
    org = OrganizationFactory()

    user = UserFactory()
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
        role=Representative.OPEN_DATA_COORDINATOR,
    )

    target_rep = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
        role=target_role,
    )

    assert target_rep.can_be_updated_by(user) is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target_role, expected",
    [
        (Representative.OPEN_DATA_COORDINATOR, True),
        (Representative.OPEN_DATA_MANAGER, True),
        (Representative.RESOURCE_COORDINATOR, False),
        (Representative.RESOURCE_MANAGER, False),
    ],
)
def test_grandparent_dataset_open_data_coordinator_can_be_updated_by(target_role, expected):
    organization = OrganizationFactory()

    grandparent_dataset = DatasetFactory(organization=organization)
    parent_dataset = DatasetFactory(organization=organization)
    child_dataset = DatasetFactory(organization=organization)
    parent_dataset.move(grandparent_dataset, pos="sorted-child")
    parent_dataset.refresh_from_db()
    child_dataset.move(parent_dataset, pos="sorted-child")
    child_dataset.refresh_from_db()
    grandparent_dataset.refresh_from_db()
    user = UserFactory()

    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(grandparent_dataset),
        object_id=grandparent_dataset.pk,
        user=user,
        role=Representative.OPEN_DATA_COORDINATOR,
    )

    target_rep = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(child_dataset),
        object_id=child_dataset.pk,
        role=target_role,
    )

    assert target_rep.can_be_updated_by(user) is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target_role",
    [
        Representative.OPEN_DATA_COORDINATOR,
        Representative.OPEN_DATA_MANAGER,
        Representative.RESOURCE_COORDINATOR,
        Representative.RESOURCE_MANAGER,
    ],
)
def test_resource_coordinator_can_update_all_roles(target_role):
    org = OrganizationFactory()

    user = UserFactory()
    RepresentativeFactory(
        user=user,
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
        role=Representative.RESOURCE_COORDINATOR,
    )

    target_rep = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
        role=target_role,
    )

    assert target_rep.can_be_updated_by(user) is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "target_role, expected",
    [
        (Representative.OPEN_DATA_COORDINATOR, True),
        (Representative.OPEN_DATA_MANAGER, True),
        (Representative.RESOURCE_COORDINATOR, True),
        (Representative.RESOURCE_MANAGER, True),
    ],
)
def test_grandparent_dataset_resource_coordinator_can_update_all_roles(target_role, expected):
    organization = OrganizationFactory()

    grandparent_dataset = DatasetFactory(organization=organization)
    parent_dataset = DatasetFactory(organization=organization)
    child_dataset = DatasetFactory(organization=organization)
    parent_dataset.move(grandparent_dataset, pos="sorted-child")
    parent_dataset.refresh_from_db()
    child_dataset.move(parent_dataset, pos="sorted-child")
    child_dataset.refresh_from_db()
    grandparent_dataset.refresh_from_db()
    user = UserFactory()

    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(grandparent_dataset),
        object_id=grandparent_dataset.pk,
        user=user,
        role=Representative.RESOURCE_COORDINATOR,
    )

    target_rep = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(child_dataset),
        object_id=child_dataset.pk,
        role=target_role,
    )

    assert target_rep.can_be_updated_by(user) is expected


@pytest.mark.django_db
def test_non_representative_cannot_update():
    org = OrganizationFactory()

    user = UserFactory()

    target_rep = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
        role=Representative.OPEN_DATA_MANAGER,
    )

    assert target_rep.can_be_updated_by(user) is False
