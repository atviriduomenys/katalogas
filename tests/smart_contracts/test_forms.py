from pathlib import Path

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset, Contact

from vitrina.orgs.models import Organization
from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory
from vitrina.smart_contracts.factories import AgreementFactory, AgreementPDFFileFactory, AgreementJSONFileFactory
from vitrina.smart_contracts.forms import SmartContractForm, AgreementUploadForm, AgreementGeneratePdfForm
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

    def test_agreement_generate_pdf_form_representative_querysets(self):
        assigner_organization = OrganizationFactory(title="Assigner Organization", email="assigner@example.com")
        assignee_organization = OrganizationFactory(title="Assignee Organization", email="assignee@example.com")

        assigner_user = UserFactory(organization=assigner_organization, email="assigner@test.com")
        assignee_user = UserFactory(organization=assignee_organization, email="assignee@test.com")

        content_type_user = ContentType.objects.get_for_model(User)

        dataset_a, dataset_b, dataset_c, dataset_d, dataset_e, dataset_f = [
            DatasetFactory(organization=assigner_organization) for _ in range(6)
        ]

        assigner_contact_user = Contact.objects.create(
            organization=assigner_organization,
            content_type=content_type_user,
            object_id=assigner_user.pk,
            email=assigner_user.email,
        )

        assignee_contact_user = Contact.objects.create(
            organization=assigner_organization,
            content_type=content_type_user,
            object_id=assignee_user.pk,
            email=assignee_user.email,
        )

        random_contact_user = Contact.objects.create(
            organization=assigner_organization,
            content_type=content_type_user,
            object_id=OrganizationFactory().pk,
            email="example@example.com",
        )

        project = ProjectFactory(organization=assignee_organization, datasets=[dataset_a, dataset_b, dataset_c, dataset_d])
        agreement = AgreementFactory(project=project, assigner=assigner_organization, assignee=assignee_organization)

        form = AgreementGeneratePdfForm(agreement=agreement)

        assigner_queryset = list(form.fields["assigner_representative"].queryset)
        assignee_queryset = list(form.fields["assignee_representative"].queryset)

        assert assigner_contact_user in assigner_queryset
        assert assignee_contact_user in assignee_queryset

        assert random_contact_user not in assigner_queryset
        assert random_contact_user not in assignee_queryset


class TestAgreementUploadForm:
    def test_not_valid_when_uploading_file_other_than_adoc(self) -> None:
        uploaded_file = SimpleUploadedFile("bad_file.md", b"md file content")
        agreement_pdf = AgreementPDFFileFactory()
        form = AgreementUploadForm(files={"file": uploaded_file}, agreement_pdf=agreement_pdf, agreement=agreement_pdf.agreement)

        assert form.is_valid() is False
        assert form.errors == {"file": ["Dokumentas turi būti adoc formato."]}

    def test_not_valid_when_uploading_unsigned_adoc(self, agreement_pdf: Path, agreement_not_signed: Path) -> None:
        agreement_pdf = AgreementPDFFileFactory(pdf_path = agreement_pdf)
        with open(agreement_not_signed, "rb") as f:
            uploaded_file = SimpleUploadedFile("sutartis_not_signed.adoc", f.read())

        form = AgreementUploadForm(files={"file": uploaded_file}, agreement_pdf=agreement_pdf, agreement=agreement_pdf.agreement)
        assert form.is_valid() is False
        assert form.errors == {"file": ["Įkelta sutartis nepasirašyta."]}
