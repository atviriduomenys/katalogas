from datetime import datetime

import pytest
import pytz
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from vitrina.classifiers.factories import ConceptFactory
from vitrina.datasets.factories import DatasetFactory, DCATResourceSubclassFactory
from vitrina.datasets.models import DCATResourceSubclass, Dataset
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestDatasets:
    def test_translations_default_language(self):
        dataset = DatasetFactory()
        default_language = dataset.get_current_language()
        assert default_language == "lt"

    def test_language_changes(self):
        dataset = DatasetFactory()
        dataset.set_current_language("en")
        current = dataset.get_current_language()
        assert current == "en"

    def test_public_manager_filtering(self):
        organization = OrganizationFactory(slug="org", kind="gov")

        DatasetFactory(is_public=False, organization=organization)
        DatasetFactory(
            deleted=True,
            deleted_on=pytz.timezone(settings.TIME_ZONE).localize(datetime.now()),
            organization=organization,
        )
        DatasetFactory(deleted=True, deleted_on=None, organization=organization)
        DatasetFactory(deleted=None, deleted_on=None, organization=organization)
        DatasetFactory(organization=organization)

        public_datasets = Dataset.public.all().exclude(id=1)
        assert public_datasets.count() == 2

    @pytest.mark.parametrize(
        "field_name",
        [
            "information_system_type",
            "information_system_importance",
        ],
    )
    def test_automatically_assign_information_system_mandatory_fields_if_not_set(self, field_name):
        dataset = DatasetFactory()
        dataset.refresh_from_db()

        value = getattr(dataset, field_name)
        assert value is not None
        assert value.code == "NOT-SET"

    @pytest.mark.parametrize(
        "field_name",
        [
            "information_system_type",
            "information_system_importance",
        ],
    )
    def test_do_not_assign_default_information_system_fields_if_it_set(self, field_name):
        concept = ConceptFactory()
        dataset = DatasetFactory(**{field_name: concept})
        dataset.refresh_from_db()

        value = getattr(dataset, field_name)
        assert value == concept

    def test_get_effective_user_role_via_org_returns_none_when_user_has_no_org_memberships(self):
        dataset = DatasetFactory()
        user = UserFactory()
        assert dataset.get_effective_user_role_via_org(user) is None

    def test_get_effective_user_role_via_org_returns_none_when_user_org_is_not_a_representative(self):
        dataset = DatasetFactory()
        user = UserFactory()
        unrelated_org = OrganizationFactory()
        org_ct = ContentType.objects.get_for_model(unrelated_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=unrelated_org.pk,
            user=user,
            organization=None,
        )
        assert dataset.get_effective_user_role_via_org(user) is None

    def test_get_effective_user_role_via_org_returns_none_when_user_belongs_to_multiple_orgs_but_none_are_representatives(
        self,
    ):
        dataset = DatasetFactory()
        user = UserFactory()

        for _ in range(3):
            org = OrganizationFactory()
            org_ct = ContentType.objects.get_for_model(org)
            RepresentativeFactory(
                content_type=org_ct,
                object_id=org.pk,
                user=user,
                organization=None,
            )

        assert dataset.get_effective_user_role_via_org(user) is None

    def test_get_effective_user_role_via_org_returns_role_when_user_org_represents_dataset(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_org(user) == Representative.RESOURCE_MANAGER

    def test_get_effective_user_role_via_org_returns_role_when_user_org_represents_dataset_organization(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset.organization),
            object_id=dataset.organization.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_org(user) == Representative.RESOURCE_MANAGER

    def test_get_effective_user_role_via_org_returns_role_when_user_org_represents_ancestor_dataset(self):
        parent = DatasetFactory()
        child = DatasetFactory()
        child.move(parent, pos="sorted-child")
        child.refresh_from_db()

        representative_org = OrganizationFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(parent),
            object_id=parent.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert child.get_effective_user_role_via_org(user) == Representative.RESOURCE_MANAGER

    def test_get_effective_user_role_via_org_returns_role_when_user_org_represents_ancestor_organization(self):
        parent = DatasetFactory()
        child = DatasetFactory(organization=parent.organization)
        child.move(parent, pos="sorted-child")
        child.refresh_from_db()

        representative_org = OrganizationFactory()
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(parent.organization),
            object_id=parent.organization.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert child.get_effective_user_role_via_org(user) == Representative.RESOURCE_MANAGER

    def test_get_effective_user_role_via_org_organization_role_lower_than_user(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_org(user) == Representative.OPEN_DATA_MANAGER

    @pytest.mark.parametrize(
        "role",
        [
            Representative.RESOURCE_MANAGER,
            Representative.OPEN_DATA_MANAGER,
        ],
    )
    def test_get_effective_user_role_via_org_returns_correct_role_for_all_role_types(self, role):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=role,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=role,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_org(user) == role

    def test_get_effective_user_role_via_org_open_data_manager_org_restricts_resource_manager_user(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.OPEN_DATA_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.RESOURCE_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_org(user) == Representative.OPEN_DATA_MANAGER

    def test_get_effective_user_role_via_org_resource_manager_org_preserves_open_data_manager_user(self):
        dataset = DatasetFactory()
        representative_org = OrganizationFactory()

        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            role=Representative.RESOURCE_MANAGER,
            organization=representative_org,
            user=None,
        )

        user = UserFactory()
        org_ct = ContentType.objects.get_for_model(representative_org)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=representative_org.pk,
            role=Representative.OPEN_DATA_MANAGER,
            user=user,
            organization=None,
        )

        assert dataset.get_effective_user_role_via_org(user) == Representative.OPEN_DATA_MANAGER


class TestDCATResourceSubclass:
    @pytest.mark.parametrize(
        "name, result",
        [
            (DCATResourceSubclass.SERIES, False),
            (DCATResourceSubclass.SERVICE, False),
            (DCATResourceSubclass.INFORMATION_SYSTEM, True),
        ],
    )
    def test_is_information_system(self, name: str, result: bool) -> None:
        subclass = DCATResourceSubclassFactory(name=name)
        assert subclass.is_information_system is result

    @pytest.mark.parametrize(
        "name, result",
        [
            (DCATResourceSubclass.SERIES, False),
            (DCATResourceSubclass.SERVICE, False),
            (DCATResourceSubclass.DATASET, True),
        ],
    )
    def test_is_dataset(self, name: str, result: bool) -> None:
        subclass = DCATResourceSubclassFactory(name=name)
        assert subclass.is_dataset is result

    @pytest.mark.parametrize(
        "name, result",
        [
            (DCATResourceSubclass.SERIES, False),
            (DCATResourceSubclass.SERVICE, False),
            (DCATResourceSubclass.CATALOG, True),
        ],
    )
    def test_is_catalog(self, name: str, result: bool) -> None:
        subclass = DCATResourceSubclassFactory(name=name)
        assert subclass.is_catalog is result
