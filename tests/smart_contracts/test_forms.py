from pathlib import Path
from typing import Type

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django_webtest import DjangoTestApp

from tests.conftest import organization
from tests.smart_contracts.conftest import agreement_pdf, ODRL_JSON
from vitrina.datasets.factories import DatasetFactory, ContactFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization
from vitrina.projects.factories import ProjectFactory
from vitrina.smart_contracts import AgreementStatuses
from vitrina.smart_contracts.factories import AgreementPDFFileFactory, AgreementFactory, AgreementJSONFileFactory
from vitrina.smart_contracts.forms import (
    SmartContractForm,
    AgreementSubmitForm,
    AgreementApproveForm,
    AgreementFormForm, AgreementInitiateForm, AgreementSignForm,
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
        dataset = DatasetFactory(organization=organization, metadata="")
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

        contact_no_user = ContactFactory(
            contact_name="Petras Petrauskas",
            organization=organization,
            content_type=None,
            object_id=None,
            email="example3@example.com",
            phone="+37060000000"
        )
        contact_with_user = ContactFactory(
            contact_name="Vardenis Pavardenis",
            organization=organization,
            object_id=user.id,
            content_type=ContentType.objects.get_for_model(User),
            email="example@example.com",
            phone="+37060000000"
        )
        contact_unrelated_organization = ContactFactory(
            contact_name="Jonas Jonauskas",
            organization=unrelated_organization,
            content_type=None,
            object_id=None,
            email="example4@example.com",
            phone="+37060000000"
        )

        # Act
        form = AgreementSubmitForm(agreement=agreement)

        # Assert
        selectable_contacts = list(form.fields["assignee_representative"].queryset)

        assert contact_no_user in selectable_contacts
        assert contact_with_user in selectable_contacts
        assert contact_unrelated_organization not in selectable_contacts

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
            content_type=None,
            object_id=None,
            email="example3@example.com",
            phone="+37060000000"
        )
        contact_unrelated_organization = ContactFactory(
            contact_name="Jonas Jonauskas",
            organization=unrelated_organization,
            content_type=None,
            object_id=None,
            email="example4@example.com",
            phone="+37060000000"
        )

        # Act
        form = AgreementApproveForm(agreement=agreement)
        contacts_selectable = list(form.fields["assigner_representative"].queryset)

        # Assert
        assert contact_no_user in contacts_selectable
        assert contact_with_user in contacts_selectable
        assert contact_unrelated_organization not in contacts_selectable

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
    @pytest.mark.parametrize(
        "form_class,agreement_status,file_name",
        [
            (AgreementInitiateForm, AgreementStatuses.FORMED, "agreement_one_signer.adoc"),
            (AgreementSignForm, AgreementStatuses.INITIATED, "agreement_two_signers.adoc")
        ],
    )
    def test_success(
        self,
        form_class: Type[AgreementInitiateForm | AgreementSignForm],
        agreement_status: AgreementStatuses,
        file_name: str,
        agreement_pdf: str
    ):
        # Arrange
        base_path = Path(__file__).parent / "files" / "test_contracts"
        test_file_path = base_path / file_name
        odrl_json_file_path = Path(__file__).parent / "files" / ODRL_JSON

        with open(test_file_path, "rb") as file:
            uploaded_file = SimpleUploadedFile("agreement_one_signer.adoc", file.read())
        agreement = AgreementFactory(status=agreement_status)
        agreement_pdf_file = AgreementPDFFileFactory(pdf_path=agreement_pdf, agreement=agreement)

        AgreementJSONFileFactory(agreement=agreement, json_path=odrl_json_file_path)

        # Act
        form = form_class(
            files={"file": uploaded_file},
            agreement_pdf=agreement_pdf_file,
            agreement=agreement,
        )

        # Assert
        assert form.is_valid()

    def test_uploaded_document_is_not_adoc(self):
        # Arrange
        uploaded_file = SimpleUploadedFile("not_adoc.md", b"content")
        agreement_pdf_file = AgreementPDFFileFactory()

        # Act
        form = AgreementInitiateForm(files={"file": uploaded_file}, agreement_pdf=agreement_pdf_file, agreement=agreement_pdf_file.agreement)

        # Assert
        assert not form.is_valid()
        assert form.errors == {"file": ["Dokumentas turi būti adoc formato."]}

    def test_bad_zip_file(self):
        # Arrange
        uploaded_file = SimpleUploadedFile("bad.adoc", b"content")
        agreement_pdf_file = AgreementPDFFileFactory()

        # Act
        form = AgreementInitiateForm(
            files={"file": uploaded_file},
            agreement_pdf=agreement_pdf_file,
            agreement=agreement_pdf_file.agreement
        )

        # Assert
        assert not form.is_valid()
        assert form.errors == {"file": ["Prisegtas failas nėra ZIP archyvas."]}

    @pytest.mark.parametrize("form_class", [AgreementInitiateForm, AgreementSignForm])
    @pytest.mark.parametrize(
        "filename,expected_error",
        [
            ("agreement_bad_certificate.adoc", "ADOC klaida: Netinkamas parašo sertifikatas."),
            ("agreement_no_manifest.adoc", "ADOC klaida: Neteisingas ADOC formatas."),
            ("agreement_two_files.adoc", "ADOC klaida: Rastas daugiau nei vienas pasirašytas dokumentas."),
            ("agreement_no_pdf.adoc", "ADOC klaida: Nerastas PDF dokumentas."),
            ("agreement_modified.adoc", "ADOC klaida: PDF dokumentas nesutampa su sutartyje esančiu PDF dokumentu."),
            ("agreement_non_zip.adoc", "Prisegtas failas nėra ZIP archyvas."),
            ("agreement_not_signed.adoc", "Įkelta sutartis nepasirašyta."),
            ("agreement.pdf", "Dokumentas turi būti adoc formato."),
        ]
    )
    def test_initiate_and_sign_form_errors(
        self,
        form_class: Type[AgreementInitiateForm | AgreementSignForm],
        filename: str,
        expected_error: str,
        agreement_pdf: str,
    ):
        """Checks both forms and all validations, that are common throughout these forms."""
        # Arrange
        base_path = Path(__file__).parent / "files" / "test_contracts"
        test_file_path = base_path / filename

        with open(test_file_path, "rb") as f:
            uploaded_file = SimpleUploadedFile(filename, f.read())
        agreement_pdf_file = AgreementPDFFileFactory(pdf_path=agreement_pdf)

        # Act
        form = form_class(
            files={"file": uploaded_file},
            agreement_pdf=agreement_pdf_file,
            agreement=agreement_pdf_file.agreement,
        )

        # Assert
        assert not form.is_valid()
        assert "file" in form.errors
        assert form.errors["file"][0] == expected_error
