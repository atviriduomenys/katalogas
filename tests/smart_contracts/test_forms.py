from pathlib import Path

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django_webtest import DjangoTestApp

from tests.conftest import organization
from vitrina.datasets.factories import DatasetFactory, ContactFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.projects.factories import ProjectFactory
from vitrina.smart_contracts.factories import AgreementPDFFileFactory, AgreementFactory
from vitrina.smart_contracts.forms import (
    SmartContractForm,
    AgreementSubmitForm,
    AgreementApproveForm,
    AgreementFormForm,
)
from vitrina.smart_contracts.models import SmartContractTemplate
from vitrina.structure.factories import MetadataFactory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User

pytestmark = pytest.mark.django_db


class TestSmartContractForm:
    def test_generates_no_scope_choices_if_dataset_metadata_by_organization_not_given(
        self, organization: Organization, dataset: Dataset
    ) -> None:
        form = SmartContractForm(instance=organization)

        assert form.fields["scopes"].choices == []

    def test_generates_no_scope_choices_if_organization_has_no_datasets(
        self, organization: Organization
    ) -> None:
        form = SmartContractForm(
            instance=organization,
            dataset_metadata_by_organization={organization.id: []},
        )

        assert form.fields["scopes"].choices == []

    def test_generates_no_scope_choices_if_dataset_metadata_has_empty_name(
        self, organization: Organization
    ) -> None:
        dataset = DatasetFactory(organization=organization)
        MetadataFactory(
            content_type=ContentType.objects.get_for_model(dataset),
            object_id=dataset.pk,
            dataset=dataset,
            name="",
        )
        form = SmartContractForm(
            instance=organization,
            dataset_metadata_by_organization={
                organization.id: [dataset.metadata.first()]
            },
        )
        assert form.fields["scopes"].choices == []

    def test_generates_scope_choices_from_each_dataset(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        form = SmartContractForm(
            instance=organization,
            dataset_metadata_by_organization={
                organization.id: [dataset.metadata.first()]
            },
        )

        assert set(form.fields["scopes"].choices) == {
            ("uapi:/test/dataset/:getall", "uapi:/test/dataset/:getall"),
            ("uapi:/test/dataset/:search", "uapi:/test/dataset/:search"),
            ("uapi:/test/dataset/:select", "uapi:/test/dataset/:select"),
        }


class TestAgreementSubmitForm:
    def test_success(self, organization: Organization):
        # Arrange
        agreement = AgreementFactory(
            assignee=organization,
            project=ProjectFactory(organization=organization),
        )
        contact = ContactFactory(
            contact_name="Vardenis Pavardenis",
            organization=organization,
            object_id=None,
            content_type=None,
            email="example@example.com",
            phone="+37060000000"
        )

        # Act
        form = AgreementSubmitForm(
            data={"assignee_representative": contact.pk},
            agreement=agreement
        )

        # Assert
        assert form.is_valid(), form.errors

    def test_assignee_representative_queryset(self, organization: Organization):
        # Arrange
        unrelated_organization = OrganizationFactory()
        agreement = AgreementFactory(
            assignee=organization,
            project=ProjectFactory(organization=organization)
        )

        user = UserFactory(organization=organization)
        contact_with_user = ContactFactory(
            contact_name="Vardenis Pavardenis",
            organization=organization,
            object_id=user.id,
            content_type=ContentType.objects.get_for_model(User),
            email="example@example.com",
            phone="+37060000000"
        )
        contact_no_user = ContactFactory(
            contact_name="Petras Petrauskas",
            organization=organization,
            content_object=user,
            email="example2@example.com",
            phone="+37060000000"
        )
        contact_unrelated_organization = ContactFactory(
            contact_name="Jonas Jonauskas",
            organization=unrelated_organization,
            object_id=None,
            content_type=None,
            email="example3@example.com",
            phone="+37060000000"
        )

        # Act
        form = AgreementSubmitForm(agreement=agreement)

        # Assert
        contacts_selectable_in_form = list(form.fields["assignee_representative"].queryset)
        assert contact_unrelated_organization not in contacts_selectable_in_form
        assert all(contact in contacts_selectable_in_form for contact in {contact_with_user, contact_no_user})

    def test_failure_required_fields_unfilled(self, organization: Organization):
        agreement = AgreementFactory(
            assignee=organization,
            project=ProjectFactory(organization=organization)
        )
        form = AgreementSubmitForm(data={}, agreement=agreement)

        assert not form.is_valid()
        assert form.errors == {"assignee_representative": ["Šis laukas yra privalomas."]}


class TestAgreementApproveForm:
    def test_success(self, organization: Organization):
        # Arrange
        template = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )
        organization = OrganizationFactory()
        agreement = AgreementFactory(
            assigner=organization,
            project=ProjectFactory(organization=organization),
        )

        contact = ContactFactory(
            contact_name="Vardenis Pavardenis",
            organization=organization,
            object_id=None,
            content_type=None,
            email="example@example.com",
            phone="+37060000000"
        )

        # Act
        form = AgreementApproveForm(
            data={
                "template": template.pk,
                "assigner_representative": contact.pk,
                "other_assigner_legislations": "Legislation A; Legislation B; Legislation C."
            },
            agreement=agreement
        )

        # Assert
        assert form.is_valid(), form.errors

    def test_assigner_representative_queryset(self, organization: Organization):
        # Arrange
        unrelated_organization = OrganizationFactory()
        agreement = AgreementFactory(
            assigner=organization,
            project=ProjectFactory(organization=organization),
        )

        user = UserFactory(
            organization=organization,
            is_viisp_login=True,
            viisp_company_code=organization.company_code,
        )
        contact_with_user = ContactFactory(
            contact_name="Vardenis Pavardenis",
            organization=organization,
            object_id=user.id,
            content_type=ContentType.objects.get_for_model(User),
            email="example@example.com",
            phone="+37060000000"
        )
        contact_no_user = ContactFactory(
            contact_name="Petras Petrauskas",
            organization=organization,
            content_object=user,
            email="example2@example.com",
            phone="+37060000000"
        )
        contact_unrelated_organization = ContactFactory(
            contact_name="Jonas Jonauskas",
            organization=unrelated_organization,
            object_id=None,
            content_type=None,
            email="example3@example.com",
            phone="+37060000000"
        )

        # Act
        form = AgreementApproveForm(agreement=agreement)

        # Assert
        contacts_selectable_in_form = list(form.fields["assigner_representative"].queryset)
        assert contact_unrelated_organization not in contacts_selectable_in_form
        assert all(contact in contacts_selectable_in_form for contact in (contact_with_user, contact_no_user))

    def test_template_queryset(self, organization: Organization):
        # Arrange
        unrelated_organization = OrganizationFactory()
        agreement = AgreementFactory(
            assigner=organization,
            project=ProjectFactory(organization=organization),
        )

        template_no_organization = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            )
        )
        template_current_organization = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            ),
            organization=organization,
        )
        template_unrelated_organization = SmartContractTemplate.objects.create(
            file=ContentFile(
                open(Path(__file__).parent / "files" / "contract_template.md").read(),
                name="contract_template.md",
            ),
            organization=unrelated_organization,
        )

        # Act
        form = AgreementApproveForm(agreement=agreement)

        # Assert
        agreements_selectable_in_form = list(form.fields["template"].queryset)
        assert template_unrelated_organization not in agreements_selectable_in_form
        assert all(
            template in agreements_selectable_in_form for template in (
                template_no_organization,
                template_current_organization,
            )
        )

    def test_failure_required_fields_unfilled(self, organization: Organization):
        # Arrange
        agreement = AgreementFactory(
            assignee=organization,
            project=ProjectFactory(organization=organization)
        )

        # Act
        form = AgreementApproveForm(data={}, agreement=agreement)

        # Assert
        assert not form.is_valid()
        assert form.errors == {
            "template": ["Šis laukas yra privalomas."],
            "assigner_representative": ["Šis laukas yra privalomas."],
            "other_assigner_legislations": ["Šis laukas yra privalomas."],
        }


class TestAgreementFormForm:
    def test_success(self, organization: Organization):
        # Arrange
        agreement = AgreementFactory(
            assignee=organization,
            project=ProjectFactory(organization=organization)
        )

        # Act
        form = AgreementFormForm(data={}, agreement=agreement)

        # Assert
        assert form.is_valid(), form.errors


class TestAgreementInitiateAndSignForms:
    """Tests for both AgreementInitiateForm and AgreementSignForm have the same logic in their respective forms."""
    def test_success(self):
        pass

    def test_adoc_error(self):
        # Raises InvalidAdocError
        pass

    def test_bad_zip_file(self):
        # Raises BadZipFile
        pass