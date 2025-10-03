import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization
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
        "user_attr,ds_attr,is_public,access_rights,expected",
        [
            # not public dataset
            ("regular_user", "grandchild", False, "PUBLIC", False),
            ("random_org_representative", "grandchild", False, "PUBLIC", False),
            ("org_representative", "grandchild", False, "PUBLIC", True),
            ("data_set_representative", "grandchild", False, "PUBLIC", True),
            ("parent_representative", "grandchild", False, "PUBLIC", True),
            ("global_representative", "grandchild", False, "PUBLIC", True),
            # public datasets
            ("regular_user", "grandchild", True, "PUBLIC", True),
            ("random_org_representative", "grandchild", True, "PUBLIC", True),
            ("org_representative", "grandchild", True, "PUBLIC", True),
            ("data_set_representative", "grandchild", True, "PUBLIC", True),
            ("parent_representative", "grandchild", True, "PUBLIC", True),
            ("global_representative", "grandchild", True, "PUBLIC", True),
            ("grandpa_rep", "grandchild", True, "PUBLIC", True),
            # restricted
            ("regular_user", "grandchild", True, "RESTRICTED", True),
            ("random_org_representative", "grandchild", True, "RESTRICTED", True),
            ("org_representative", "grandchild", True, "RESTRICTED", True),
            ("data_set_representative", "grandchild", True, "RESTRICTED", True),
            ("parent_representative", "grandchild", True, "RESTRICTED", True),
            ("global_representative", "grandchild", True, "RESTRICTED", True),
            # non-public
            ("regular_user", "grandchild", True, "NON_PUBLIC", False),
            ("random_org_representative", "grandchild", True, "NON_PUBLIC", True),
            ("org_representative", "grandchild", True, "NON_PUBLIC", True),
            ("data_set_representative", "grandchild", True, "NON_PUBLIC", True),
            ("parent_representative", "grandchild", True, "NON_PUBLIC", True),
            ("global_representative", "grandchild", True, "NON_PUBLIC", True),
            # confidential
            ("regular_user", "grandchild", True, "CONFIDENTIAL", False),
            ("random_org_representative", "grandchild", True, "CONFIDENTIAL", False),
            ("org_representative", "grandchild", True, "CONFIDENTIAL", True),
            ("data_set_representative", "grandchild", True, "CONFIDENTIAL", True),
            ("parent_representative", "grandchild", True, "CONFIDENTIAL", True),
            ("global_representative", "grandchild", True, "CONFIDENTIAL", True),
        ],
    )
    def test_view_permissions(
        self,
        user_attr: str,
        ds_attr: str,
        is_public: bool,
        access_rights: str,
        expected: bool,
    ):
        user = getattr(self, user_attr)
        ds = getattr(self, ds_attr)

        ds.is_public = is_public
        ds.access_rights = access_rights
        ds.save()

        qs = Dataset.restricted.for_user(user)
        result = ds in qs

        assert result is expected
