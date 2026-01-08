import pytest
from django.contrib.contenttypes.models import ContentType

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
def test_non_representative_cannot_update():
    org = OrganizationFactory()

    user = UserFactory()

    target_rep = RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
        role=Representative.OPEN_DATA_MANAGER,
    )

    assert target_rep.can_be_updated_by(user) is False
