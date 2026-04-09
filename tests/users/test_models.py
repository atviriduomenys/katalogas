from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory


class TestIsOpenDataRepresentativeFor:
    def test_returns_false_if_obj_is_none(self):
        user = UserFactory()
        assert user.is_open_data_representative_for(None) is False

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
            role=Representative.RESOURCE_COORDINATOR,
        )

        assert user.is_open_data_representative_for(organization) is False

    def test_returns_true_if_users_organization_represents_organization(self):
        organization = OrganizationFactory()
        user_organization = OrganizationFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(user_organization),
            object_id=user_organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

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
            role=Representative.RESOURCE_COORDINATOR,
        )

        assert user.is_open_data_representative_for(dataset) is False

    def test_returns_true_if_users_organization_represents_dataset(self):
        dataset = DatasetFactory()
        user_organization = OrganizationFactory()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(user_organization),
            object_id=user_organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

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

    def test_returns_true_if_user_represents_datasets_organization_with_open_data_role_on_dataset(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            organization=organization,
            role=Representative.OPEN_DATA_MANAGER,
        )

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(dataset) is True

    def test_returns_true_if_datasets_organization_holds_resource_role_on_dataset(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            organization=organization,
            role=Representative.RESOURCE_MANAGER,
        )

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(organization),
            object_id=organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(dataset) is True

    def test_returns_false_if_user_is_not_representative_of_datasets_organization(self):
        organization = OrganizationFactory()
        other_organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            organization=organization,
            role=Representative.OPEN_DATA_MANAGER,
        )

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(other_organization),
            object_id=other_organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(dataset) is False

    def test_returns_true_if_user_represents_parent_dataset(self):
        parent_dataset = DatasetFactory()
        child_dataset = DatasetFactory()
        child_dataset.move(parent_dataset, pos="sorted-child")
        child_dataset.refresh_from_db()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(parent_dataset),
            object_id=parent_dataset.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(child_dataset) is True

    def test_returns_true_if_user_represents_grandparent_dataset(self):
        grandparent_dataset = DatasetFactory()
        parent_dataset = DatasetFactory()
        child_dataset = DatasetFactory()
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
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(child_dataset) is True

    def test_returns_false_if_user_represents_child_but_not_parent(self):
        parent_dataset = DatasetFactory()
        child_dataset = DatasetFactory()
        child_dataset.move(parent_dataset, pos="sorted-child")
        child_dataset.refresh_from_db()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(child_dataset),
            object_id=child_dataset.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(parent_dataset) is False

    def test_returns_true_if_users_organization_represents_parent_dataset(self):
        user_organization = OrganizationFactory()
        parent_dataset = DatasetFactory()
        child_dataset = DatasetFactory()
        child_dataset.move(parent_dataset, pos="sorted-child")
        child_dataset.refresh_from_db()
        user = UserFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(user_organization),
            object_id=user_organization.pk,
            user=user,
            role=Representative.OPEN_DATA_MANAGER,
        )

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(parent_dataset),
            object_id=parent_dataset.pk,
            organization=user_organization,
            role=Representative.OPEN_DATA_MANAGER,
        )

        assert user.is_open_data_representative_for(child_dataset) is True
