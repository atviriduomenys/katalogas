import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.orgs.factories import RepresentativeFactory, OrganizationFactory
from vitrina.orgs.models import Organization, Representative
from vitrina.projects.factories import ProjectFactory
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.smart_contracts.permissions import can_create_agreements, can_submit_agreements, can_approve_agreements, \
    can_form_agreements
from vitrina.users.factories import UserFactory


class TestCanCreateAgreements:
    def test_success(self, organization: Organization):
        user = UserFactory(is_viisp_login=True, viisp_company_code=organization.company_code)
        project = ProjectFactory(organization=organization)
        RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.COORDINATOR,
            can_make_agreements=True,
            object_id=organization.id,
            content_type=ContentType.objects.get_for_model(organization)
        )

        assert can_create_agreements(user, project)

    def test_no_organization_provided(self, organization: Organization):
        user = UserFactory()
        project = ProjectFactory(organization=None)
        RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.COORDINATOR,
            can_make_agreements=True,
            object_id=organization.id,
            content_type=ContentType.objects.get_for_model(organization)
        )

        assert not can_create_agreements(user, project)

    def test_not_viisp_authenticated(self, organization: Organization):
        user = UserFactory(is_viisp_login=False, viisp_company_code="invalid_company_code")
        project = ProjectFactory(organization=organization)
        RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.COORDINATOR,
            can_make_agreements=True,
            object_id=organization.id,
            content_type=ContentType.objects.get_for_model(organization)
        )

        assert not can_create_agreements(user, project)

    def test_not_representative(self, organization: Organization):
        user = UserFactory(is_viisp_login=False, viisp_company_code="invalid_company_code")
        project = ProjectFactory(organization=organization)

        assert not can_create_agreements(user, project)


class TestCanSubmitAgreements:
    def test_success(self, organization: Organization):
        user = UserFactory(is_viisp_login=True, viisp_company_code=organization.company_code)
        agreement = AgreementFactory(
            assignee=organization,
            project=ProjectFactory(organization=organization),
        )
        RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.COORDINATOR,
            can_make_agreements=True,
            object_id=organization.id,
            content_type=ContentType.objects.get_for_model(organization)
        )

        assert can_submit_agreements(user, agreement)

    def test_not_viisp_authenticated(self, organization: Organization):
        user = UserFactory(is_viisp_login=False, viisp_company_code="invalid_company_code")
        agreement = AgreementFactory(
            assignee=organization,
            project=ProjectFactory(organization=organization),
        )
        RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.COORDINATOR,
            can_make_agreements=True,
            object_id=organization.id,
            content_type=ContentType.objects.get_for_model(organization)
        )

        assert not can_submit_agreements(user, agreement)

    def test_not_representative(self, organization: Organization):
        user = UserFactory(is_viisp_login=True, viisp_company_code=organization.company_code)
        agreement = AgreementFactory(
            assignee=organization,
            project=ProjectFactory(organization=organization),
        )

        assert not can_submit_agreements(user, agreement)


class TestCanApproveAgreements:
    def test_success(self, organization: Organization):
        user = UserFactory(is_viisp_login=True, viisp_company_code=organization.company_code)
        agreement = AgreementFactory(
            assigner=organization,
            project=ProjectFactory(organization=organization),
        )
        RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.COORDINATOR,
            can_make_agreements=True,
            object_id=organization.id,
            content_type=ContentType.objects.get_for_model(organization)
        )

        assert can_approve_agreements(user, agreement)

    def test_not_viisp_authenticated(self, organization: Organization):
        user = UserFactory(is_viisp_login=False, viisp_company_code="invalid_company_code")
        agreement = AgreementFactory(
            assignee=organization,
            project=ProjectFactory(organization=organization),
        )
        RepresentativeFactory(
            user=user,
            organization=organization,
            role=Representative.COORDINATOR,
            can_make_agreements=True,
            object_id=organization.id,
            content_type=ContentType.objects.get_for_model(organization)
        )

        assert not can_approve_agreements(user, agreement)

    def test_not_representative(self, organization: Organization):
        user = UserFactory(is_viisp_login=True, viisp_company_code=organization.company_code)
        agreement = AgreementFactory(
            assigner=organization,
            project=ProjectFactory(organization=organization),
        )

        assert not can_approve_agreements(user, agreement)


class TestCanFormAgreements:
    @pytest.mark.parametrize("is_acting_user_assignee", [True, False])
    def test_success(self, is_acting_user_assignee: bool):
        assignee = OrganizationFactory()
        assigner = OrganizationFactory()

        user = UserFactory(
            is_viisp_login=True,
            organization=assignee if is_acting_user_assignee else assigner,
            viisp_company_code=assignee.company_code if is_acting_user_assignee else assigner.company_code,
        )

        agreement = AgreementFactory(
            assignee=assignee,
            assigner=assigner,
            project=ProjectFactory(organization=assignee),
        )

        RepresentativeFactory(
            user=user,
            organization=assignee if is_acting_user_assignee else assigner,
            role=Representative.COORDINATOR,
            can_make_agreements=True,
            object_id=assignee.id if is_acting_user_assignee else assigner.id,
            content_type=ContentType.objects.get_for_model(assignee)
        )

        assert can_form_agreements(user, agreement)

    @pytest.mark.parametrize("is_acting_user_assignee", [True, False])
    def test_not_viisp_authenticated(self, is_acting_user_assignee: bool):
        assignee = OrganizationFactory()
        assigner = OrganizationFactory()

        user = UserFactory(
            is_viisp_login=True,
            organization=assignee if is_acting_user_assignee else assigner,
            viisp_company_code="invalid_company_code",
        )

        agreement = AgreementFactory(
            assignee=assignee,
            assigner=assigner,
            project=ProjectFactory(organization=assignee),
        )

        RepresentativeFactory(
            user=user,
            organization=assignee if is_acting_user_assignee else assigner,
            role=Representative.COORDINATOR,
            can_make_agreements=True,
            object_id=assignee.id if is_acting_user_assignee else assigner.id,
            content_type=ContentType.objects.get_for_model(assignee)
        )

        assert not can_form_agreements(user, agreement)

    @pytest.mark.parametrize("is_acting_user_assignee", [True, False])
    def test_not_representative(self, is_acting_user_assignee: bool):
        assignee = OrganizationFactory()
        assigner = OrganizationFactory()

        user = UserFactory(
            is_viisp_login=True,
            organization=assignee if is_acting_user_assignee else assigner,
            viisp_company_code=assignee.company_code if is_acting_user_assignee else assigner.company_code,
        )

        agreement = AgreementFactory(
            assignee=assignee,
            assigner=assigner,
            project=ProjectFactory(organization=assignee),
        )

        assert not can_form_agreements(user, agreement)
