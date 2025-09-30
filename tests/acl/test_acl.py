import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization
from vitrina.orgs.services import Action, has_perm
from vitrina.users.models import User

@pytest.mark.django_db
class TestDatasetAccessControl:
    def setup_method(self):
        main_organization = OrganizationFactory()
        random_organization = OrganizationFactory()
        random_organization.kind = Organization.GOV
        random_organization.save()
        grand_organization = OrganizationFactory()

        self.grand_parent = DatasetFactory(is_public=True, organization=grand_organization)

        self.parent = DatasetFactory(is_public=False, organization=main_organization)
        self.parent.move(self.grand_parent, pos='sorted-child')
        self.parent.refresh_from_db()

        self.child = DatasetFactory(is_public=False, organization=main_organization)
        self.child.move(self.parent, pos='sorted-child')
        self.child.refresh_from_db()

        self.grandchild = DatasetFactory(is_public=False, organization=main_organization)
        self.grandchild.move(self.child, pos='sorted-child')
        self.grandchild.refresh_from_db()

        self.regular_user = User.objects.create_user(email="test@test.com", password="test123", status=User.ACTIVE)
        self.random_org_representative = User.objects.create_user(email="test2@test.com", password="test123", status=User.ACTIVE)
        self.org_representative = User.objects.create_user(email="test3@test.com", password="test123", status=User.ACTIVE)
        self.data_set_representative = User.objects.create_user(email="test4@test.com", password="test123", status=User.ACTIVE)
        self.parent_representative = User.objects.create_user(email="test5@test.com", password="test123", status=User.ACTIVE)
        self.global_representative = User.objects.create_user(email="vssa@vssa.com", password="vssa123", status=User.ACTIVE, is_staff=True)
        self.grandpa_rep = User.objects.create_user(email="vssa2@vssa.com", password="vssa123", status=User.ACTIVE)

        self.repr_random_org = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(random_organization),
            object_id=random_organization.pk,
            user=self.random_org_representative
        )

        self. repr_org = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(main_organization),
            object_id=main_organization.pk,
            user=self.org_representative
        )
        self.repr_ds = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.grandchild),
            object_id=self.grandchild.pk,
            user=self.data_set_representative
        )
        self.repr_parent = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(self.parent),
            object_id=self.parent.pk,
            user=self.parent_representative
        )
        self.repr_grand_org = RepresentativeFactory(
            content_type=ContentType.objects.get_for_model(grand_organization),
            object_id=grand_organization.pk,
            user=self.grandpa_rep
        )


    def can_view(self, user: User, dataset: Dataset) -> bool:
        return has_perm(user, Action.VIEW, dataset)

    def can_update(self, user: User, dataset: Dataset) -> bool:
        return has_perm(user, Action.UPDATE, dataset)

    def can_create(self, user: User, dataset: Dataset) -> bool:
        return has_perm(user, Action.CREATE, dataset)

    @pytest.mark.parametrize(
        "user_attr,ds_attr,is_public_value,access_rights_value,expected",
        [
            pytest.param("regular_user", "grandchild",False, "PUBLIC", False, id="view, not public: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",False, "PUBLIC", False, id="view, not public: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",False, "PUBLIC", True, id="view, not public: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",False, "PUBLIC", True, id="view, not public: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",False, "PUBLIC", True, id="view, not public: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",False, "PUBLIC", True, id="view, not public: global_rep -> grandchild"),

            pytest.param("regular_user", "grandchild",True, "PUBLIC", True, id="view, ar_public: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",True, "PUBLIC", True, id="view, ar_public: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",True, "PUBLIC", True, id="view, ar_public: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",True, "PUBLIC", True, id="view, ar_public: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",True, "PUBLIC", True, id="view, ar_public: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",True, "PUBLIC", True, id="view, ar_public: global_rep -> grandchild"),
            pytest.param("grandpa_rep", "grandchild",True, "PUBLIC", True, id="view, ar_public: grandpa_rep -> grandchild"),

            pytest.param("regular_user", "grandchild",True, "RESTRICTED", True, id="view, ar_restricted: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",True, "RESTRICTED", True, id="view, ar_restricted: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",True, "RESTRICTED", True, id="view, ar_restricted: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",True, "RESTRICTED", True, id="view, ar_restricted: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",True, "RESTRICTED", True, id="view, ar_restricted: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",True, "RESTRICTED", True, id="view, ar_restricted: global_rep -> grandchild"),

            pytest.param("regular_user", "grandchild",True, "NON_PUBLIC", False, id="view, ar_non_public: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",True, "NON_PUBLIC", True, id="view, ar_non_public: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",True, "NON_PUBLIC", True, id="view, ar_non_public: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",True, "NON_PUBLIC", True, id="view, ar_non_public: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",True, "NON_PUBLIC", True, id="view, ar_non_public: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",True, "NON_PUBLIC", True, id="view, ar_non_public: global_rep -> grandchild"),

            pytest.param("regular_user", "grandchild",True, "CONFIDENTIAL", False, id="view, ar_confidential: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",True, "CONFIDENTIAL", False, id="view, ar_confidential: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",True, "CONFIDENTIAL", True, id="view, ar_confidential: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",True, "CONFIDENTIAL", True, id="view, ar_confidential: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",True, "CONFIDENTIAL", True, id="view, ar_confidential: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",True, "CONFIDENTIAL", True, id="view, ar_confidential: global_rep -> grandchild"),
        ],
    )
    def test_view_permissions(self, user_attr: str, ds_attr:str, is_public_value: bool, access_rights_value: str,  expected: bool):
        user = getattr(self, user_attr)
        ds = getattr(self, ds_attr)

        ds.is_public = is_public_value
        ds.access_rights = access_rights_value
        ds.save()

        result = self.can_view(user, ds)
        assert result is expected, f"view {user_attr} -> {ds_attr}: expected {expected}, got {result}"



    @pytest.mark.parametrize(
        "user_attr,ds_attr,is_public_value,access_rights_value,expected",
        [
            pytest.param("regular_user", "grandchild",False, "PUBLIC", False, id="update, not public: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",False, "PUBLIC", False, id="update, not public: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",False, "PUBLIC", True, id="update, not public: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",False, "PUBLIC", True, id="update, not public: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",False, "PUBLIC", True, id="update, not public: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",False, "PUBLIC", True, id="update, not public: global_rep -> grandchild"),

            pytest.param("regular_user", "grandchild",True, "PUBLIC", True, id="update, ar_public: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",True, "PUBLIC", True, id="update, ar_public: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",True, "PUBLIC", True, id="update, ar_public: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",True, "PUBLIC", True, id="update, ar_public: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",True, "PUBLIC", True, id="update, ar_public: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",True, "PUBLIC", True, id="update, ar_public: global_rep -> grandchild"),
            pytest.param("grandpa_rep", "grandchild",True, "PUBLIC", True, id="update, ar_public: grandpa_rep -> grandchild"),

            pytest.param("regular_user", "grandchild",True, "RESTRICTED", True, id="update, ar_restricted: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",True, "RESTRICTED", True, id="update, ar_restricted: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",True, "RESTRICTED", True, id="update, ar_restricted: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",True, "RESTRICTED", True, id="update, ar_restricted: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",True, "RESTRICTED", True, id="update, ar_restricted: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",True, "RESTRICTED", True, id="update, ar_restricted: global_rep -> grandchild"),

            pytest.param("regular_user", "grandchild",True, "NON_PUBLIC", False, id="update, ar_non_public: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",True, "NON_PUBLIC", True, id="update, ar_non_public: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",True, "NON_PUBLIC", True, id="update, ar_non_public: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",True, "NON_PUBLIC", True, id="update, ar_non_public: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",True, "NON_PUBLIC", True, id="update, ar_non_public: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",True, "NON_PUBLIC", True, id="update, ar_non_public: global_rep -> grandchild"),

            pytest.param("regular_user", "grandchild",True, "CONFIDENTIAL", False, id="update, ar_confidential: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",True, "CONFIDENTIAL", False, id="update, ar_confidential: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",True, "CONFIDENTIAL", False, id="update, ar_confidential: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",True, "CONFIDENTIAL", False, id="update, ar_confidential: dataset_rep -> grandchild"),
            pytest.param("parent_representative", "grandchild",True, "CONFIDENTIAL", False, id="update, ar_confidential: parent_dataset_rep -> grandchild"),
            pytest.param("global_representative", "grandchild",True, "CONFIDENTIAL", False, id="update, ar_confidential: global_rep -> grandchild"),
        ],
    )
    def test_update_permissions(self, user_attr: str, ds_attr: str, is_public_value: bool, access_rights_value: str, expected: bool):
        user = getattr(self, user_attr)
        ds = getattr(self, ds_attr)

        ds.is_public = is_public_value
        ds.access_rights = access_rights_value
        ds.save()

        result = self.can_update(user, ds)
        assert result is expected, f"update {user_attr} -> {ds_attr}: expected {expected}, got {result}"


    @pytest.mark.parametrize(
        "user_attr,ds_attr,is_public_value,access_rights_value,expected",
        [
            pytest.param("regular_user", "grandchild",True, "CONFIDENTIAL", False, id="update, ar_confidential: regular -> grandchild"),
            pytest.param("random_org_representative", "grandchild",True, "CONFIDENTIAL", False, id="update, ar_confidential: random_org -> grandchild"),
            pytest.param("org_representative", "grandchild",True, "CONFIDENTIAL", True, id="update, ar_confidential: org_representative -> grandchild"),
            pytest.param("data_set_representative", "grandchild",True, "CONFIDENTIAL", True, id="update, ar_confidential: dataset_rep -> grandchild"),
            pytest.param("grandpa_rep", "grandchild", True, "CONFIDENTIAL", True, id="update, ar_confidential: grandpa_rep -> grandchild"),
        ],
    )
    def test_update_confidential_with_permissions(self, user_attr: str, ds_attr: str, is_public_value: bool, access_rights_value: str, expected: bool):

        self.repr_random_org.can_write = True
        self.repr_random_org.save()
        self.repr_org.can_write = True
        self.repr_org.save()
        self.repr_ds.can_write = True
        self.repr_ds.save()
        self.repr_parent.can_write = True
        self.repr_parent.save()
        self.repr_grand_org.can_write = True
        self.repr_grand_org.save()

        user = getattr(self, user_attr)
        ds = getattr(self, ds_attr)

        ds.is_public = is_public_value
        ds.access_rights = access_rights_value
        ds.save()

        result = self.can_update(user, ds)
        assert result is expected, f"update {user_attr} -> {ds_attr}: expected {expected}, got {result}"