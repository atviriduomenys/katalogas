from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory


class TestIsOpenDataRepresentativeFor:
    def test_returns_false_if_obj_is_none(self):
        user = UserFactory()
        assert user.is_open_data_representative_for(None) is False

    # Organization tests
    def test_returns_true_if_user_is_direct_representative_of_organization(self):
        organization = OrganizationFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(organization) is True

    def test_returns_true_if_user_is_coordinator_of_organization(self):
        organization = OrganizationFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            user=user,
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        assert user.is_open_data_representative_for(organization) is True

    def test_returns_false_if_user_representative_is_deleted_for_organization(self):
        organization = OrganizationFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
            deleted=True,
        )

        assert user.is_open_data_representative_for(organization) is False

    def test_returns_false_if_user_has_non_open_data_role_for_organization(self):
        organization = OrganizationFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            user=user,
            role=Representative.RESOURCE_COORDINATOR,  # non open data role
        )

        assert user.is_open_data_representative_for(organization) is False

    def test_returns_true_if_users_organization_represents_organization(self):
        organization = OrganizationFactory()
        user_organization = OrganizationFactory()
        user = UserFactory()

        # user belongs to user_organization
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(user_organization),
            object_id=user_organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        # user_organization represents organization
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            organization=user_organization,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(organization) is True

    def test_returns_false_if_user_has_no_representatives_for_organization(self):
        organization = OrganizationFactory()
        user = UserFactory()

        assert user.is_open_data_representative_for(organization) is False

    # Dataset tests
    def test_returns_true_if_user_is_direct_representative_of_dataset(self):
        dataset = DatasetFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(dataset) is True

    def test_returns_true_if_user_is_coordinator_of_dataset(self):
        dataset = DatasetFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        assert user.is_open_data_representative_for(dataset) is True

    def test_returns_false_if_user_representative_is_deleted_for_dataset(self):
        dataset = DatasetFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
            deleted=True,
        )

        assert user.is_open_data_representative_for(dataset) is False

    def test_returns_false_if_user_has_non_open_data_role_for_dataset(self):
        dataset = DatasetFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            user=user,
            role=Representative.RESOURCE_COORDINATOR,  # non open data role
        )

        assert user.is_open_data_representative_for(dataset) is False

    def test_returns_true_if_users_organization_represents_dataset(self):
        dataset = DatasetFactory()
        user_organization = OrganizationFactory()
        user = UserFactory()

        # user belongs to user_organization
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(user_organization),
            object_id=user_organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        # user_organization represents dataset
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            organization=user_organization,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(dataset) is True

    def test_returns_false_if_user_has_no_representatives_for_dataset(self):
        dataset = DatasetFactory()
        user = UserFactory()

        assert user.is_open_data_representative_for(dataset) is False
