import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization, Representative
from vitrina.users.models import User


@pytest.mark.django_db
class TestDatasetViewPermissions:
    def setup_method(self):
        self.main_organization = OrganizationFactory(kind=Organization.COM)
        self.random_organization = OrganizationFactory(kind=Organization.GOV)
        self.grand_organization = OrganizationFactory(kind=Organization.COM)

        # Create dataset hierarchy
        self.grand_parent = DatasetFactory(is_public=True, organization=self.grand_organization)

        self.parent = DatasetFactory(is_public=False, organization=self.main_organization)
        self.parent.move(self.grand_parent, pos="sorted-child")
        self.parent.refresh_from_db()

        self.child = DatasetFactory(is_public=False, organization=self.main_organization)
        self.child.move(self.parent, pos="sorted-child")
        self.child.refresh_from_db()

        self.grandchild = DatasetFactory(is_public=False, organization=self.main_organization)
        self.grandchild.move(self.child, pos="sorted-child")
        self.grandchild.refresh_from_db()

        # Create users
        self.regular_user = User.objects.create_user(email="test@test.com", password="test123", status=User.ACTIVE)
        self.random_org_representative = User.objects.create_user(
            email="test2@test.com", password="test123", status=User.ACTIVE
        )
        self.org_representative = User.objects.create_user(
            email="test3@test.com", password="test123", status=User.ACTIVE
        )
        self.data_set_representative = User.objects.create_user(
            email="test4@test.com", password="test123", status=User.ACTIVE
        )
        self.parent_representative = User.objects.create_user(
            email="test5@test.com", password="test123", status=User.ACTIVE
        )
        self.global_representative = User.objects.create_user(
            email="vssa@vssa.com", password="vssa123", status=User.ACTIVE, is_staff=True
        )
        self.grandpa_rep = User.objects.create_user(email="vssa2@vssa.com", password="vssa123", status=User.ACTIVE)

        # Create representatives
        self.repr_random_org = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.random_organization),
            object_id=self.random_organization.pk,
            user=self.random_org_representative,
        )

        self.repr_org = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.main_organization),
            object_id=self.main_organization.pk,
            user=self.org_representative,
        )

        self.repr_ds = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.grandchild),
            object_id=self.grandchild.pk,
            user=self.data_set_representative,
        )

        self.repr_parent = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.parent),
            object_id=self.parent.pk,
            user=self.parent_representative,
        )

        self.repr_grand_org = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.grand_organization),
            object_id=self.grand_organization.pk,
            user=self.grandpa_rep,
        )

    @pytest.mark.parametrize(
        "user_attributes,dataset_attributes,is_public,access_rights,subclass,expected",
        [
            # not public dataset
            ("regular_user", "grandchild", False, "PUBLIC", "dataset", False),
            ("random_org_representative", "grandchild", False, "PUBLIC", "dataset", False),
            ("org_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("global_representative", "grandchild", False, "PUBLIC", "dataset", True),
            # public datasets
            ("regular_user", "grandchild", True, "PUBLIC", "dataset", True),
            ("random_org_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("org_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("global_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("grandpa_rep", "grandchild", True, "PUBLIC", "dataset", True),
            # restricted
            ("regular_user", "grandchild", True, "RESTRICTED", "dataset", True),
            ("random_org_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("org_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("data_set_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("parent_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("global_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            # non-public
            ("regular_user", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("random_org_representative", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("org_representative", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("data_set_representative", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("parent_representative", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("global_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            # confidential
            ("regular_user", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("random_org_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("org_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("data_set_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("parent_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("global_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
        ],
    )
    def test_view_permissions_open_data_managers(
        self,
        user_attributes: str,
        dataset_attributes: str,
        is_public: bool,
        access_rights: str,
        subclass: str,
        expected: bool,
    ):
        user = getattr(self, user_attributes)
        dataset = getattr(self, dataset_attributes)

        dataset.is_public = is_public
        dataset.access_rights = access_rights
        dataset.subclass_id = DCATResourceSubclass.objects.get(name=subclass).pk
        dataset.save()

        queryset = Dataset.restricted.for_user(user)
        result = dataset in queryset

        assert result is expected

    @pytest.mark.parametrize(
        "user_attributes,dataset_attributes,is_public,access_rights,subclass,expected",
        [
            # not public dataset
            ("regular_user", "grandchild", False, "PUBLIC", "dataset", False),
            ("random_org_representative", "grandchild", False, "PUBLIC", "dataset", False),
            ("org_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("global_representative", "grandchild", False, "PUBLIC", "dataset", True),
            # public datasets
            ("regular_user", "grandchild", True, "PUBLIC", "dataset", True),
            ("random_org_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("org_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("global_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("grandpa_rep", "grandchild", True, "PUBLIC", "dataset", True),
            # restricted
            ("regular_user", "grandchild", True, "RESTRICTED", "dataset", True),
            ("random_org_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("org_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("data_set_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("parent_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("global_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            # non-public
            ("regular_user", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("random_org_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            ("org_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            ("global_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            # confidential
            ("regular_user", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("random_org_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("org_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
            ("data_set_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
            ("parent_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
            ("global_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
        ],
    )
    def test_view_permissions_resource_managers(
        self,
        user_attributes: str,
        dataset_attributes: str,
        is_public: bool,
        access_rights: str,
        subclass: str,
        expected: bool,
    ):
        for repr_ in (
            self.repr_random_org,
            self.repr_org,
            self.repr_ds,
            self.repr_parent,
            self.repr_grand_org,
        ):
            repr_.role = Representative.RESOURCE_MANAGER
            repr_.save(update_fields=["role"])
        user = getattr(self, user_attributes)
        dataset = getattr(self, dataset_attributes)

        dataset.is_public = is_public
        dataset.access_rights = access_rights
        dataset.subclass_id = DCATResourceSubclass.objects.get(name=subclass).pk
        dataset.save()

        queryset = Dataset.restricted.for_user(user)
        result = dataset in queryset

        assert result is expected


@pytest.mark.django_db
class TestDatasetViewPermissionsViaOrgRepresentative:
    def setup_method(self):
        self.main_organization = OrganizationFactory(kind=Organization.COM)
        self.random_organization = OrganizationFactory(kind=Organization.GOV)
        self.grand_organization = OrganizationFactory(kind=Organization.COM)

        # Create dataset hierarchy
        self.grand_parent = DatasetFactory(is_public=True, organization=self.grand_organization)

        self.parent = DatasetFactory(is_public=False, organization=self.main_organization)
        self.parent.move(self.grand_parent, pos="sorted-child")
        self.parent.refresh_from_db()

        self.child = DatasetFactory(is_public=False, organization=self.main_organization)
        self.child.move(self.parent, pos="sorted-child")
        self.child.refresh_from_db()

        self.grandchild = DatasetFactory(is_public=False, organization=self.main_organization)
        self.grandchild.move(self.child, pos="sorted-child")
        self.grandchild.refresh_from_db()

        # Create users
        self.regular_user = User.objects.create_user(email="test@test.com", password="test123", status=User.ACTIVE)
        self.global_representative = User.objects.create_user(
            email="vssa@vssa.com", password="vssa123", status=User.ACTIVE, is_staff=True
        )

        # Create representative orgs
        self.random_rep_org = OrganizationFactory()
        self.main_rep_org = OrganizationFactory()
        self.grandchild_rep_org = OrganizationFactory()
        self.parent_rep_org = OrganizationFactory()
        self.grand_rep_org = OrganizationFactory()

        # Assign rep orgs to resources
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.random_organization),
            object_id=self.random_organization.pk,
            organization=self.random_rep_org,
            user=None,
        )
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.main_organization),
            object_id=self.main_organization.pk,
            organization=self.main_rep_org,
            user=None,
        )
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.grandchild),
            object_id=self.grandchild.pk,
            organization=self.grandchild_rep_org,
            user=None,
        )
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.parent),
            object_id=self.parent.pk,
            organization=self.parent_rep_org,
            user=None,
        )
        RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.grand_organization),
            object_id=self.grand_organization.pk,
            organization=self.grand_rep_org,
            user=None,
        )

        org_ct = ContentType.objects.get_for_model(self.random_rep_org)

        # Create users as members of their respective rep orgs
        self.random_org_representative = User.objects.create_user(
            email="test2@test.com", password="test123", status=User.ACTIVE
        )
        RepresentativeFactory(
            content_type=org_ct,
            object_id=self.random_rep_org.pk,
            user=self.random_org_representative,
            organization=None,
        )

        self.org_representative = User.objects.create_user(
            email="test3@test.com", password="test123", status=User.ACTIVE
        )
        RepresentativeFactory(
            content_type=org_ct,
            object_id=self.main_rep_org.pk,
            user=self.org_representative,
            organization=None,
        )

        self.data_set_representative = User.objects.create_user(
            email="test4@test.com", password="test123", status=User.ACTIVE
        )
        RepresentativeFactory(
            content_type=org_ct,
            object_id=self.grandchild_rep_org.pk,
            user=self.data_set_representative,
            organization=None,
        )

        self.parent_representative = User.objects.create_user(
            email="test5@test.com", password="test123", status=User.ACTIVE
        )
        RepresentativeFactory(
            content_type=org_ct,
            object_id=self.parent_rep_org.pk,
            user=self.parent_representative,
            organization=None,
        )

        self.grandpa_rep = User.objects.create_user(email="vssa2@vssa.com", password="vssa123", status=User.ACTIVE)
        RepresentativeFactory(
            content_type=org_ct,
            object_id=self.grand_rep_org.pk,
            user=self.grandpa_rep,
            organization=None,
        )

    @pytest.mark.parametrize(
        "user_attributes,dataset_attributes,is_public,access_rights,subclass,expected",
        [
            # not public dataset
            ("regular_user", "grandchild", False, "PUBLIC", "dataset", False),
            ("random_org_representative", "grandchild", False, "PUBLIC", "dataset", False),
            ("org_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("global_representative", "grandchild", False, "PUBLIC", "dataset", True),
            # public datasets
            ("regular_user", "grandchild", True, "PUBLIC", "dataset", True),
            ("random_org_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("org_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("global_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("grandpa_rep", "grandchild", True, "PUBLIC", "dataset", True),
            # restricted
            ("regular_user", "grandchild", True, "RESTRICTED", "dataset", True),
            ("random_org_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("org_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("data_set_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("parent_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("global_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            # non-public
            ("regular_user", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("random_org_representative", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("org_representative", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("data_set_representative", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("parent_representative", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("global_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            # confidential
            ("regular_user", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("random_org_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("org_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("data_set_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("parent_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("global_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
        ],
    )
    def test_view_permissions_open_data_managers(
        self, user_attributes, dataset_attributes, is_public, access_rights, subclass, expected
    ):
        user = getattr(self, user_attributes)
        dataset = getattr(self, dataset_attributes)
        dataset.is_public = is_public
        dataset.access_rights = access_rights
        dataset.subclass_id = DCATResourceSubclass.objects.get(name=subclass).pk
        dataset.save()

        queryset = Dataset.restricted.for_user(user)
        assert (dataset in queryset) is expected

    @pytest.mark.parametrize(
        "user_attributes,dataset_attributes,is_public,access_rights,subclass,expected",
        [
            # not public dataset
            ("regular_user", "grandchild", False, "PUBLIC", "dataset", False),
            ("random_org_representative", "grandchild", False, "PUBLIC", "dataset", False),
            ("org_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", False, "PUBLIC", "dataset", True),
            ("global_representative", "grandchild", False, "PUBLIC", "dataset", True),
            # public datasets
            ("regular_user", "grandchild", True, "PUBLIC", "dataset", True),
            ("random_org_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("org_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("global_representative", "grandchild", True, "PUBLIC", "dataset", True),
            ("grandpa_rep", "grandchild", True, "PUBLIC", "dataset", True),
            # restricted
            ("regular_user", "grandchild", True, "RESTRICTED", "dataset", True),
            ("random_org_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("org_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("data_set_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("parent_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            ("global_representative", "grandchild", True, "RESTRICTED", "dataset", True),
            # non-public
            ("regular_user", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("random_org_representative", "grandchild", True, "NON_PUBLIC", "dataset", False),
            ("org_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            ("data_set_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            ("parent_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            ("global_representative", "grandchild", True, "NON_PUBLIC", "dataset", True),
            # confidential
            ("regular_user", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("random_org_representative", "grandchild", True, "CONFIDENTIAL", "dataset", False),
            ("org_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
            ("data_set_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
            ("parent_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
            ("global_representative", "grandchild", True, "CONFIDENTIAL", "dataset", True),
        ],
    )
    def test_view_permissions_resource_managers(
        self, user_attributes, dataset_attributes, is_public, access_rights, subclass, expected
    ):
        for rep_org in (
            self.random_rep_org,
            self.main_rep_org,
            self.grandchild_rep_org,
            self.parent_rep_org,
            self.grand_rep_org,
        ):
            Representative.objects.filter(organization=rep_org).update(role=Representative.RESOURCE_MANAGER)
            Representative.objects.filter(
                content_type=ContentType.objects.get_for_model(rep_org),
                object_id=rep_org.pk,
            ).update(role=Representative.RESOURCE_MANAGER)

        user = getattr(self, user_attributes)
        dataset = getattr(self, dataset_attributes)
        dataset.is_public = is_public
        dataset.access_rights = access_rights
        dataset.subclass_id = DCATResourceSubclass.objects.get(name=subclass).pk
        dataset.save()

        queryset = Dataset.restricted.for_user(user)
        assert (dataset in queryset) is expected
