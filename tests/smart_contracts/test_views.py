import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from webtest import Upload
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.urls import reverse
from django_webtest import DjangoTestApp
from pdfminer.high_level import extract_text

from vitrina.datasets.factories import DatasetFactory, ContactFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory, ViispRepresentativeFactory
from vitrina.orgs.models import Organization
from vitrina.projects.factories import ProjectFactory
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementFactory, AgreementPDFFileFactory, AgreementJSONFileFactory
from vitrina.smart_contracts.models import (
    Agreement,
    AgreementScope,
    SmartContractTemplate,
)
from vitrina.structure.factories import MetadataFactory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User
from tests.smart_contracts.constants import SIGNER1_FULL_NAME, SIGNER2_FULL_NAME

pytestmark = pytest.mark.django_db
test_contracts_dir = Path(__file__).parent / "files" / "test_contracts"


class TestAgreementListView:
    def test_cannot_list_for_personal_project(self, app: DjangoTestApp) -> None:
        user = UserFactory()
        project = ProjectFactory(user=user)
        app.set_user(user)

        response = app.get(
            reverse("agreement-list", args=[project.pk]), expect_errors=True
        )
        assert response.status_code == 403

    def test_cannot_list_no_permission(self, app: DjangoTestApp, organization: Organization) -> None:
        user = UserFactory()
        project = ProjectFactory(user=user, organization=organization)
        app.set_user(user)

        response = app.get(
            reverse("agreement-list", args=[project.pk]), expect_errors=True
        )
        assert response.status_code == 403

    def test_list_agreements_as_assignee(
        self, app: DjangoTestApp, organization: Organization) -> None:
        user =  UserFactory()
        RepresentativeFactory(user=user, content_object=organization)
        project = ProjectFactory(organization=organization)
        app.set_user(user)
        AgreementFactory.create_batch(2, project=project, assignee=organization, assigner=OrganizationFactory())

        response = app.get(reverse("agreement-list", args=[project.pk]))

        assert response.status_code == 200
        assert project.agreements.count() == 2
        assert response.context["agreements"].count() == 2

    def test_list_no_agreements(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        representative = RepresentativeFactory(content_object=organization)
        user =  representative.user
        project = ProjectFactory(organization=organization, datasets=[dataset])
        app.set_user(user)

        response = app.get(reverse("agreement-list", args=[project.pk]))

        assert response.status_code == 200
        assert response.context["agreements"].count() == 0

    def test_list_agreements_as_assigner(self, app: DjangoTestApp, organization: Organization) -> None:
        user =  UserFactory()
        RepresentativeFactory(user=user, content_object=organization)
        project = ProjectFactory(organization=OrganizationFactory())
        app.set_user(user)
        AgreementFactory(project=project, assigner=organization)
        AgreementFactory(project=project, assigner=OrganizationFactory())

        response = app.get(reverse("agreement-list", args=[project.pk]))

        assert response.status_code == 200
        assert project.agreements.count() == 2
        assert response.context["agreements"].count() == 1


class TestAgreementDetailView:
    def test_cannot_show_details_without_permission(
        self, app: DjangoTestApp, organization: Organization
    ) -> None:
        user = UserFactory()
        app.set_user(user)
        project = ProjectFactory()
        agreement = AgreementFactory(project=project, assigner=organization)

        response = app.get(
            reverse("agreement-detail", args=[project.pk, agreement.pk]),
            expect_errors=True,
        )
        assert response.status_code == 403

    def test_http_404_when_agreement_does_not_exist(self, app: DjangoTestApp) -> None:
        user = UserFactory()
        app.set_user(user)
        project = ProjectFactory()

        response = app.get(
            reverse("agreement-detail", args=[project.pk, uuid4()]), expect_errors=True
        )
        assert response.status_code == 404

    def test_http_404_when_agreement_does_not_exist_in_project(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        app.set_user(user)
        project = ProjectFactory(user=user, datasets=[dataset])
        agreement = AgreementFactory(project=project, assigner=organization)
        different_project = ProjectFactory()

        response = app.get(
            reverse("agreement-detail", args=[different_project.pk, agreement.pk]),
            expect_errors=True,
        )
        assert response.status_code == 404

    def test_agreement_details(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        user = UserFactory(organization=organization)
        RepresentativeFactory(user=user, content_object=organization)
        app.set_user(user)
        project = ProjectFactory(organization=organization, datasets=[dataset])
        agreement = AgreementFactory(project=project, assigner=organization)

        response = app.get(reverse("agreement-detail", args=[project.pk, agreement.pk]))
        assert response.status_code == 200
        assert response.context["agreement"] == agreement


class TestAgreementCreateView:
    def test_cannot_create_agreement_without_permission(
        self, app: DjangoTestApp
    ) -> None:
        representative = ViispRepresentativeFactory(can_make_agreements=False)
        user = representative.user
        project = ProjectFactory(user=user, organization=representative.content_object)
        app.set_user(user)

        response = app.get(
            reverse("agreement-create", args=[project.pk]), expect_errors=True
        )
        assert response.status_code == 403

    def test_cannot_create_agreement_for_deleted_project(
        self, app: DjangoTestApp
    ) -> None:
        representative = ViispRepresentativeFactory(can_make_agreements=True)
        user = representative.user
        project = ProjectFactory(user=user, organization=representative.content_object, deleted=True)
        app.set_user(user)

        response = app.get(
            reverse("agreement-create", args=[project.pk]), expect_errors=True
        )
        assert response.status_code == 404

    def test_cannot_create_agreements_if_all_organizations_already_has_agreement(
        self, app: DjangoTestApp, organization: Organization
    ) -> None:
        representative = ViispRepresentativeFactory(content_object=organization, can_make_agreements=True)
        user = representative.user
        project = ProjectFactory(organization=organization)
        AgreementFactory(project=project, assigner=organization)
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        assert response.status_code == 302
        assert response.url == reverse("agreement-list", args=[project.pk])

    def test_creates_agreement_and_scopes(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        representative = ViispRepresentativeFactory(content_object=organization, can_make_agreements=True)
        user = representative.user
        project = ProjectFactory(datasets=[dataset], organization=organization)
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        form = response.forms["agreement-create"]
        form["form-0-scopes"] = ["uapi:/test/dataset/:getall"]
        response = form.submit()

        assert response.status_code == 302
        assert response.url == reverse("agreement-list", args=[project.pk])

        agreement = Agreement.objects.get(project=project, assigner=organization)
        assert agreement.status == AgreementStatuses.CREATED
        assert agreement.is_agent_sync_enabled is False
        assert agreement.scopes.count() == 1

        agreement_scope = agreement.scopes.first()
        assert agreement_scope.resource == "uapi:/test/dataset"
        assert agreement_scope.action == "getall"
        assert agreement_scope.scope == "uapi:/test/dataset/:getall"

    def test_creates_multiple_agreements_and_scopes(
        self, app: DjangoTestApp, organization: Organization
    ) -> None:
        dataset1 = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset1),
            object_id=dataset1.pk,
            dataset=dataset1,
            name="test/dataset1",
        )
        dataset2 = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset2),
            object_id=dataset2.pk,
            dataset=dataset2,
            name="test/dataset2",
        )
        diff_organization = OrganizationFactory()
        diff_dataset = DatasetFactory(organization=diff_organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(diff_dataset),
            object_id=diff_dataset.pk,
            dataset=diff_dataset,
            name="datasets/gov/org/dataset",
        )
        representative = ViispRepresentativeFactory(content_object=organization, can_make_agreements=True)
        user = representative.user
        project = ProjectFactory(datasets=[dataset1, dataset2, diff_dataset], organization=organization)
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        form = response.forms["agreement-create"]
        form["form-0-scopes"] = [
            "uapi:/test/dataset1/:getall",
            "uapi:/test/dataset2/:search",
            "uapi:/test/dataset2/:select",
        ]
        form["form-1-scopes"] = ["uapi:/datasets/gov/org/dataset/:getall"]
        response = form.submit()

        assert response.status_code == 302
        assert response.url == reverse("agreement-list", args=[project.pk])

        assert Agreement.objects.filter(project=project).count() == 2
        assert set(
            AgreementScope.objects.filter(agreement__assigner=organization).values_list(
                "scope", flat=True
            )
        ) == {"uapi:/test/dataset1/:getall", "uapi:/test/dataset2/:search", "uapi:/test/dataset2/:select"}
        assert set(
            AgreementScope.objects.filter(
                agreement__assigner=diff_organization
            ).values_list("scope", flat=True)
        ) == {"uapi:/datasets/gov/org/dataset/:getall"}

    def test_can_create_agreements_for_organizations_that_currently_do_not_have_one(
        self, app: DjangoTestApp, dataset: Dataset, organization: Organization
    ) -> None:
        representative = ViispRepresentativeFactory(content_object=organization, can_make_agreements=True)
        user = representative.user
        app.set_user(user)
        organization2 = OrganizationFactory()
        dataset2 = DatasetFactory(organization=organization2)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset2),
            object_id=dataset2.pk,
            dataset=dataset2,
            name="test/dataset2",
        )
        project = ProjectFactory(datasets=[dataset, dataset2], organization=organization)
        AgreementFactory(project=project, assigner=organization)

        response = app.get(reverse("agreement-create", args=[project.pk]))
        form = response.forms["agreement-create"]

        assert form.fields.get("form-0-scopes")
        assert not form.fields.get("form-1-scopes")

    def test_cannot_create_agreement_with_invalid_scopes(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        representative = ViispRepresentativeFactory(content_object=organization, can_make_agreements=True)
        user = representative.user
        project = ProjectFactory(datasets=[dataset], organization=organization)
        app.set_user(user)

        data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 1,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
            "form-0-id": organization.id,
            "form-0-scopes": ["bad_scope"],
        }
        response = app.post(reverse("agreement-create", args=[project.pk]), data)

        assert response.status_code == 200
        assert Agreement.objects.filter(project=project).count() == 0

    def test_create_agreement_for_personal_project(
        self, app: DjangoTestApp, dataset: Dataset
    ) -> None:
        user = UserFactory()
        project = ProjectFactory(user=user, datasets=[dataset])
        app.set_user(user)

        response = app.get(reverse("agreement-create", args=[project.pk]), status=403)

        assert response.status_code == 403


class TestAgreementSubmit:
    def test_success(self, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        app.set_user(user)
        RepresentativeFactory(user=user, content_object=assignee_organization, can_make_agreements=True)
        contact = ContactFactory(
            organization=assignee_organization,
            object_id=user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=user.email,
            phone=user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )
        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=None,
            assigner=assigner_organization,
            created_by=user,
            status=AgreementStatuses.CREATED
        )

        # Act
        response = app.post(
            reverse("agreement-submit", args=[project.pk, agreement.pk]),
            {
                "assignee_representative": contact.pk
            }
        )

        # Assert
        assert response.status_code == 302
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.SUBMITTED
        assert agreement.assignee_representative == contact

    def test_unauthorized_not_representative(self, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        app.set_user(user)
        contact = ContactFactory(
            organization=assignee_organization,
            object_id=user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=user.email,
            phone=user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )
        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=None,
            assigner=assigner_organization,
            created_by=user,
            status=AgreementStatuses.CREATED
        )

        # Act
        response = app.post(
            reverse("agreement-submit", args=[project.pk, agreement.pk]),
            {
                "assignee_representative": contact.pk,
            },
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.CREATED
        assert not agreement.assignee_representative

    def test_unauthorized_not_viisp_authorized(self, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=False,
            viisp_company_code="invalid_company_code",
        )
        app.set_user(user)
        RepresentativeFactory(user=user, content_object=assignee_organization, can_make_agreements=True)
        contact = ContactFactory(
            organization=assignee_organization,
            object_id=user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=user.email,
            phone=user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )
        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=None,
            assigner=assigner_organization,
            created_by=user,
            status=AgreementStatuses.CREATED
        )

        # Act
        response = app.post(
            reverse("agreement-submit", args=[project.pk, agreement.pk]),
            {
                "assignee_representative": contact.pk
            },
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.CREATED
        assert not agreement.assignee_representative

    def test_unauthorized_not_granted_agreement_signing_rights(self, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        app.set_user(user)
        RepresentativeFactory(user=user, content_object=assignee_organization, can_make_agreements=False)
        contact = ContactFactory(
            organization=assignee_organization,
            object_id=user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=user.email,
            phone=user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )
        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=None,
            assigner=assigner_organization,
            created_by=user,
            status=AgreementStatuses.CREATED
        )

        # Act
        response = app.post(
            reverse("agreement-submit", args=[project.pk, agreement.pk]),
            {
                "assignee_representative": contact.pk
            },
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.CREATED
        assert not agreement.assignee_representative

    @pytest.mark.parametrize("initial_agreement_status", [
        AgreementStatuses.SUBMITTED,
        AgreementStatuses.APPROVED,
        AgreementStatuses.FORMED,
        AgreementStatuses.INITIATED,
        AgreementStatuses.SIGNED,
        AgreementStatuses.ACTIVE,
        AgreementStatuses.TERMINATED,
    ])
    def test_incorrect_agreement_status(
        self,
        initial_agreement_status: AgreementStatuses,
        app: DjangoTestApp,
        dataset: Dataset,
    ):
        # Arrange
        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        app.set_user(user)
        RepresentativeFactory(user=user, content_object=assignee_organization, can_make_agreements=True)
        contact = ContactFactory(
            organization=assignee_organization,
            object_id=user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=user.email,
            phone=user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )
        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=None,
            assigner=assigner_organization,
            created_by=user,
            status=initial_agreement_status
        )

        # Act
        response = app.post(
            reverse("agreement-submit", args=[project.pk, agreement.pk]),
            {
                "assignee_representative": contact.pk
            }
        )

        # Assert
        assert response.status_code == 302  # Still redirects to the success page, just with an error message.
        agreement.refresh_from_db()
        assert not agreement.assignee_representative
        assert agreement.status == initial_agreement_status


class TestAgreementApprove:
    def test_success(self, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assigner_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner_representative=None,
            assigner=assigner_organization,
            created_by=assignee_user,
            status=AgreementStatuses.SUBMITTED
        )
        other_assigner_legislations = "Legislation A; Legislation B; Legislation C."

        # Act
        response = app.post(
            reverse("agreement-approve", args=[project.pk, agreement.pk]),
            {
                "template": template.pk,
                "assigner_representative": assigner_contact.pk,
                "other_assigner_legislations": other_assigner_legislations
            }
        )

        # Assert
        assert response.status_code == 302
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.APPROVED
        assert agreement.template == template
        assert agreement.assigner_representative == assigner_contact
        assert agreement.other_assigner_legislations == other_assigner_legislations


    def test_unauthorized_not_representative(self, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assigner_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner_representative=None,
            assigner=assigner_organization,
            created_by=assignee_user,
            status=AgreementStatuses.SUBMITTED
        )
        other_assigner_legislations = "Legislation A; Legislation B; Legislation C."

        # Act
        response = app.post(
            reverse("agreement-approve", args=[project.pk, agreement.pk]),
            {
                "template": template.pk,
                "assigner_representative": assigner_contact.pk,
                "other_assigner_legislations": other_assigner_legislations
            },
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.SUBMITTED
        assert not agreement.template
        assert not agreement.assigner_representative
        assert not agreement.other_assigner_legislations

    def test_unauthorized_not_viisp_authorized(self, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=False,
            viisp_company_code="invalid_company_code",
        )
        app.set_user(assigner_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner_representative=None,
            assigner=assigner_organization,
            created_by=assignee_user,
            status=AgreementStatuses.SUBMITTED
        )
        other_assigner_legislations = "Legislation A; Legislation B; Legislation C."

        # Act
        response = app.post(
            reverse("agreement-approve", args=[project.pk, agreement.pk]),
            {
                "template": template.pk,
                "assigner_representative": assigner_contact.pk,
                "other_assigner_legislations": other_assigner_legislations
            },
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.SUBMITTED
        assert not agreement.template
        assert not agreement.assigner_representative
        assert not agreement.other_assigner_legislations

    def test_unauthorized_not_granted_agreement_signing_rights(self, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assigner_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=False)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner_representative=None,
            assigner=assigner_organization,
            created_by=assignee_user,
            status=AgreementStatuses.SUBMITTED
        )
        other_assigner_legislations = "Legislation A; Legislation B; Legislation C."

        # Act
        response = app.post(
            reverse("agreement-approve", args=[project.pk, agreement.pk]),
            {
                "template": template.pk,
                "assigner_representative": assigner_contact.pk,
                "other_assigner_legislations": other_assigner_legislations
            },
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.SUBMITTED
        assert not agreement.template
        assert not agreement.assigner_representative
        assert not agreement.other_assigner_legislations

    @pytest.mark.parametrize("initial_agreement_status", [
        AgreementStatuses.CREATED,
        AgreementStatuses.APPROVED,
        AgreementStatuses.FORMED,
        AgreementStatuses.INITIATED,
        AgreementStatuses.SIGNED,
        AgreementStatuses.ACTIVE,
        AgreementStatuses.TERMINATED,
    ])
    def test_incorrect_agreement_status(
        self,
        initial_agreement_status: AgreementStatuses,
        app: DjangoTestApp,
        dataset: Dataset
    ):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assigner_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner_representative=None,
            assigner=assigner_organization,
            created_by=assignee_user,
            status=initial_agreement_status
        )
        other_assigner_legislations = "Legislation A; Legislation B; Legislation C."

        # Act
        response = app.post(
            reverse("agreement-approve", args=[project.pk, agreement.pk]),
            {
                "template": template.pk,
                "assigner_representative": assigner_contact.pk,
                "other_assigner_legislations": other_assigner_legislations
            }
        )

        # Assert
        assert response.status_code == 302  # Still redirects to the success page, just with an error message.
        agreement.refresh_from_db()
        assert agreement.status == initial_agreement_status
        assert not agreement.template
        assert not agreement.assigner_representative
        assert not agreement.other_assigner_legislations


class TestAgreementForm:
    @pytest.mark.parametrize("is_acting_user_assignee", [True, False])
    def test_success(self, is_acting_user_assignee: bool, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        dataset.organization = assigner_organization
        dataset.save()
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assignee_user if is_acting_user_assignee else assigner_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            other_assigner_legislations="Legislation D; Legislation E; Legislation F.",
            payment_terms="Payment term A; Payment term B.",
            created_by=assignee_user,
            status=AgreementStatuses.APPROVED,
        )

        # Act
        response = app.post(
            reverse("agreement-form", args=[project.pk, agreement.pk]),
            {}
        )

        # Assert
        assert response.status_code == 302
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.FORMED

        odrl_file, contract, template_copy = list(agreement.files.order_by("is_template", "created_at"))

        assert odrl_file.file_name.endswith(".json")
        odrl_content = json.loads(odrl_file.file.read())
        assert odrl_content == {
            "@context": {
                "@vocab": "http://www.w3.org/ns/odrl.jsonld",
                "ex": "http://example.org/vocab#",
            },
            "uid": f"https://data.gov.lt/ID/datasets/gov/vssa/isris/dcat/Agreement/{agreement.pk}",
            "type": "Agreement",
            "profile": "http://www.w3.org/ns/odrl/profile/core",
            "issued": odrl_content["issued"],
            "assigner": [
                {
                    "uid": str(assigner_organization.pk),
                    "ex:companyName": assigner_organization.title,
                    "ex:companyCode": assigner_organization.company_code,
                    "ex:address": assigner_organization.address,
                    "ex:representative": agreement.assigner_representative_full_name,
                    "ex:email": assigner_organization.email,
                    "ex:phone": assigner_organization.phone,
                    "ex:personalCode": " - ",
                }
            ],
            "assignee": [
                {
                    "uid": str(assignee_organization.pk),
                    "ex:companyName": assignee_organization.title,
                    "ex:companyCode": assignee_organization.company_code,
                    "ex:address": assignee_organization.address,
                    "ex:representative": agreement.assignee_representative_full_name,
                    "ex:email": assignee_organization.email,
                    "ex:phone": assignee_organization.phone,
                    "ex:personalCode": " - ",
                }
            ],
            "permission": [
                {
                    "target": {
                        "uid": dataset.pk,
                        "ex:name": dataset.title,
                        "ex:scopes": [],
                    }
                }
            ],
            "ex:paymentTerms": agreement.payment_terms,
            "ex:otherAssignerLegislations": agreement.other_assigner_legislations,
            "ex:otherAssigneeLegislations": project.other_assignee_legislations,
        }

        assert not contract.is_template
        assert contract.checksum
        contract.file.seek(0)
        contract_content = extract_text(BytesIO(contract.file.read()))
        expected_contract_values = [
            odrl_content["issued"],
            odrl_content["assigner"][0]["ex:companyName"],
            odrl_content["assigner"][0]["ex:companyCode"],
            odrl_content["assigner"][0]["ex:address"].split("\n")[0],
            odrl_content["assigner"][0]["ex:email"],
            odrl_content["assigner"][0]["ex:phone"],
            odrl_content["assigner"][0]["ex:representative"],
            odrl_content["assigner"][0]["ex:personalCode"],
            odrl_content["assignee"][0]["ex:companyName"],
            odrl_content["assignee"][0]["ex:companyCode"],
            odrl_content["assignee"][0]["ex:address"].split("\n")[0],
            odrl_content["assignee"][0]["ex:email"],
            odrl_content["assignee"][0]["ex:phone"],
            odrl_content["assignee"][0]["ex:representative"],
            odrl_content["assignee"][0]["ex:personalCode"],
            odrl_content["permission"][0]["target"]["ex:name"],
            *odrl_content["permission"][0]["target"].get("ex:scopes", []),
            odrl_content["ex:paymentTerms"],
            odrl_content["ex:otherAssignerLegislations"],
            odrl_content["ex:otherAssigneeLegislations"],
        ]
        # Ensure all required values from odrl were transferred to the contract.
        for index, value in enumerate(expected_contract_values):
            if value := str(value).strip():
                assert value in contract_content, f"Expected '{value}' (index={index}) not found in PDF."

        assert template_copy.is_template
        assert template_copy.file.path != template.file.path
        assert template_copy.file.read() == template.file.read()
        assert template_copy.checksum

    @pytest.mark.parametrize("is_acting_user_assignee", [True, False])
    def test_unauthorized_not_representative(self, is_acting_user_assignee: bool, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        dataset.organization = assigner_organization
        dataset.save()
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assignee_user if is_acting_user_assignee else assigner_user)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            other_assigner_legislations="Legislation D; Legislation E; Legislation F.",
            payment_terms="Payment term A; Payment term B.",
            created_by=assignee_user,
            status=AgreementStatuses.APPROVED,
        )

        # Act
        response = app.post(
            reverse("agreement-form", args=[project.pk, agreement.pk]),
            {},
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.APPROVED  # Unchanged.
        assert not agreement.files.exists()

    @pytest.mark.parametrize("is_acting_user_assignee", [True, False])
    def test_unauthorized_not_viisp_authorized(self, is_acting_user_assignee: bool, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        dataset.organization = assigner_organization
        dataset.save()
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=False,
            viisp_company_code="invalid_company_code",
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=False,
            viisp_company_code="invalid_company_code",
        )
        app.set_user(assignee_user if is_acting_user_assignee else assigner_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            other_assigner_legislations="Legislation D; Legislation E; Legislation F.",
            payment_terms="Payment term A; Payment term B.",
            created_by=assignee_user,
            status=AgreementStatuses.APPROVED,
        )

        # Act
        response = app.post(
            reverse("agreement-form", args=[project.pk, agreement.pk]),
            {},
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.APPROVED  # Unchanged.
        assert not agreement.files.exists()

    @pytest.mark.parametrize("is_acting_user_assignee", [True, False])
    def test_unauthorized_not_granted_agreement_signing_rights(self, is_acting_user_assignee: bool, app: DjangoTestApp, dataset: Dataset):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        dataset.organization = assigner_organization
        dataset.save()
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assignee_user if is_acting_user_assignee else assigner_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=False)
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=False)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            other_assigner_legislations="Legislation D; Legislation E; Legislation F.",
            payment_terms="Payment term A; Payment term B.",
            created_by=assignee_user,
            status=AgreementStatuses.APPROVED,
        )

        # Act
        response = app.post(
            reverse("agreement-form", args=[project.pk, agreement.pk]),
            {},
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 403
        agreement.refresh_from_db()
        assert agreement.status == AgreementStatuses.APPROVED  # Unchanged.
        assert not agreement.files.exists()

    @pytest.mark.parametrize("initial_agreement_status", [
        AgreementStatuses.CREATED,
        AgreementStatuses.SUBMITTED,
        AgreementStatuses.FORMED,
        AgreementStatuses.INITIATED,
        AgreementStatuses.SIGNED,
        AgreementStatuses.ACTIVE,
        AgreementStatuses.TERMINATED,
    ])
    def test_incorrect_agreement_status(self, initial_agreement_status: AgreementStatuses, app: DjangoTestApp, dataset: Dataset):
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )

        assignee_organization, assigner_organization = OrganizationFactory.create_batch(2)
        dataset.organization = assigner_organization
        dataset.save()
        assignee_user = UserFactory(
            organization=assignee_organization,
            is_viisp_login=True,
            viisp_company_code=assignee_organization.company_code,
        )
        assigner_user = UserFactory(
            organization=assigner_organization,
            is_viisp_login=True,
            viisp_company_code=assigner_organization.company_code,
        )
        app.set_user(assignee_user)

        RepresentativeFactory(user=assignee_user, content_object=assignee_organization, can_make_agreements=True)
        RepresentativeFactory(user=assigner_user, content_object=assigner_organization, can_make_agreements=True)

        assignee_contact = ContactFactory(
            organization=assignee_organization,
            object_id=assignee_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assignee_user.email,
            phone=assignee_user.phone
        )
        assigner_contact = ContactFactory(
            organization=assigner_organization,
            object_id=assigner_user.pk,
            content_type=ContentType.objects.get_for_model(User),
            email=assigner_user.email,
            phone=assigner_user.phone,
        )

        project = ProjectFactory(
            organization=assignee_organization,
            datasets=[dataset],
            other_assignee_legislations="Test",
        )

        agreement = AgreementFactory(
            template=template,
            project=project,
            assignee=assignee_organization,
            assignee_representative=assignee_contact,
            assigner=assigner_organization,
            assigner_representative=assigner_contact,
            other_assigner_legislations="Legislation D; Legislation E; Legislation F.",
            payment_terms="Payment term A; Payment term B.",
            created_by=assignee_user,
            status=initial_agreement_status,
        )

        # Act
        response = app.post(
            reverse("agreement-form", args=[project.pk, agreement.pk]),
            {},
            expect_errors=True,
        )

        # Assert
        assert response.status_code == 302  # Still redirects to the success page, just with an error message.
        agreement.refresh_from_db()
        assert agreement.status == initial_agreement_status  # Unchanged.
        assert not agreement.files.exists()


class TestAgreementInitiate:
    def test_success(self):
        pass


class TestAgreementSign:
    def test_success(self):
        pass


# @pytest.mark.parametrize(
#         "agreement_choice,expected_error",
#         [
#             ("agreement_bad_certificate", "ADOC klaida: Netinkamas parašo sertifikatas."),
#             ("agreement_modified", "ADOC klaida: PDF dokumentas nesutampa su sutartyje esančiu PDF dokumentu."),
#             ("agreement_no_manifest", "ADOC klaida: Neteisingas ADOC formatas."),
#             ("agreement_no_pdf", "ADOC klaida: Nerastas PDF dokumentas."),
#             ("agreement_not_signed", "Įkelta sutartis nepasirašyta."),
#             ("agreement_two_files", "ADOC klaida: Rastas daugiau nei vienas pasirašytas dokumentas."),
#             ("agreement_two_signers", "Įkelta sutartis pasirašyta daugiau nei 1 parašu. Gavėjas turėtų pasirašyti tik vienu parašu."),
#             ("agreement_pdf", "Dokumentas turi būti adoc formato."),
#             ("agreement_non_zip", "Prisegtas failas nėra ZIP archyvas."),
#             ("agreement_one_signer", "Nesutampa pasirašiusių asmenų vardai ir pavardės. Reikalingi parašai: ['Jonas Jonaitis'], ADOC rasti parašai: ['Vardenis Pavardenis'].")
#         ],
#         indirect=["agreement_choice"]
#     )
#     def test_upload_agreement_with_errors(
#         self,
#         app: DjangoTestApp,
#         organization: Organization,
#         dataset: Dataset,
#         agreement_pdf: Path,
#         agreement_choice: Path,
#         odrl_json_wrong_representatives: Path,
#         expected_error: str
#     ) -> None:
#         representative = ViispRepresentativeFactory(content_object=organization, can_make_agreements=True)
#         user = representative.user
#         app.set_user(user)
#         project = ProjectFactory(organization=organization, datasets=[dataset])
#         contact = ContactFactory(contact_name="Jonas Jonaitis", content_type=None, object_id=None)
#         agreement = AgreementFactory(
#             project=project, assignee=organization, status=AgreementStatuses.FORMED, assignee_representative=contact
#         )
#         AgreementJSONFileFactory(agreement=agreement, json_path=odrl_json_wrong_representatives)
#         AgreementPDFFileFactory(agreement=agreement, pdf_path=agreement_pdf)
#         adoc_to_upload = Upload(
#             agreement_choice.name,
#             agreement_choice.read_bytes(),
#             content_type="text/plain",
#         )
#         response = app.get(
#             reverse("agreement-upload-signed-adoc", args=[project.pk, agreement.pk]),
#         )
#
#         form = response.forms["agreement-upload-form"]
#         form["file"] = adoc_to_upload
#         response = form.submit()
#
#         assert response.status_code == 200
#         errors = response.context["form"].errors
#
#         assert "file" in errors
#         assert errors["file"][0] == expected_error