import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType

from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.orgs.permissions import can_view_organization_agreements, can_view_organization_agreement
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.users.factories import UserFactory


class TestCanViewOrganizationAgreements:
    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_COORDINATOR,
            Representative.RESOURCE_COORDINATOR,
        ],
    )
    def test_success_representative(self, role: str):
        organization = OrganizationFactory()
        user = UserFactory()
        RepresentativeFactory(
            user=user,
            organization=organization,
            role=role,
            can_make_agreements=True,
            object_id=organization.id,
            content_type=ContentType.objects.get_for_model(organization),
        )
        assert can_view_organization_agreements(user, organization)

    def test_success_staff_or_superuser(self):
        organization = OrganizationFactory()
        staff_user = UserFactory(is_staff=True)
        super_user = UserFactory(is_superuser=True)

        assert can_view_organization_agreements(staff_user, organization)
        assert can_view_organization_agreements(super_user, organization)

    def test_user_unauthenticated(self):
        organization = OrganizationFactory()
        user = AnonymousUser()
        assert not can_view_organization_agreements(user, organization)

    def test_user_not_representative(self):
        organization = OrganizationFactory()
        user = UserFactory()
        other_organization = OrganizationFactory()
        RepresentativeFactory(
            user=user,
            organization=other_organization,
            role=Representative.OPEN_DATA_COORDINATOR,
            can_make_agreements=True,
            object_id=other_organization.id,
            content_type=ContentType.objects.get_for_model(other_organization),
        )
        assert not can_view_organization_agreements(user, organization)


class TestCanViewOrganizationAgreement:
    def test_anonymous_user_cannot_view(self):
        organization = OrganizationFactory()
        agreement = AgreementFactory(assignee=organization)
        user = AnonymousUser()
        assert not can_view_organization_agreement(user, agreement)

    def test_staff_can_view_any_agreement(self):
        organization = OrganizationFactory()
        agreement = AgreementFactory(assignee=organization)
        staff_user = UserFactory(is_staff=True)
        super_user = UserFactory(is_superuser=True)

        assert can_view_organization_agreement(staff_user, agreement)
        assert can_view_organization_agreement(super_user, agreement)

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_COORDINATOR,
            Representative.RESOURCE_COORDINATOR,
        ],
    )
    def test_user_representative_of_assignee_can_view(self, role: str):
        organization = OrganizationFactory()
        user = UserFactory()
        agreement = AgreementFactory(assignee=organization)

        RepresentativeFactory(
            user=user,
            organization=organization,
            role=role,
            can_make_agreements=True,
            object_id=organization.id,
            content_type=ContentType.objects.get_for_model(organization),
        )

        assert can_view_organization_agreement(user, agreement)

    @pytest.mark.parametrize(
        "role",
        [
            Representative.OPEN_DATA_COORDINATOR,
            Representative.RESOURCE_COORDINATOR,
        ],
    )
    def test_user_representative_of_assigner_can_view(self, role: str):
        assignee = OrganizationFactory()
        assigner = OrganizationFactory()
        user = UserFactory()
        agreement = AgreementFactory(assignee=assignee, assigner=assigner)

        RepresentativeFactory(
            user=user,
            organization=assigner,
            role=role,
            can_make_agreements=True,
            object_id=assigner.id,
            content_type=ContentType.objects.get_for_model(assigner),
        )

        assert can_view_organization_agreement(user, agreement)

    def test_user_not_representative_cannot_view(self):
        assignee = OrganizationFactory()
        assigner = OrganizationFactory()
        user = UserFactory()
        agreement = AgreementFactory(assignee=assignee, assigner=assigner)

        other_organization = OrganizationFactory()
        RepresentativeFactory(
            user=user,
            organization=other_organization,
            role=Representative.OPEN_DATA_COORDINATOR,
            can_make_agreements=True,
            object_id=other_organization.id,
            content_type=ContentType.objects.get_for_model(other_organization),
        )

        assert not can_view_organization_agreement(user, agreement)
