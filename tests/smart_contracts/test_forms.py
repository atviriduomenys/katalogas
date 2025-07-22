import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Organization
from vitrina.smart_contracts.forms import SmartContractForm, AgreementUploadForm
from vitrina.structure.factories import MetadataFactory

pytestmark = pytest.mark.django_db


class TestSmartContractForm:
    def test_generates_no_scope_choices_if_datasets_by_organization_not_given(
        self, organization: Organization, dataset: Dataset
    ) -> None:
        form = SmartContractForm(instance=organization)

        assert form.fields["scopes"].choices == []

    def test_generates_no_scope_choices_if_organization_has_no_datasets(
        self, organization: Organization
    ) -> None:
        form = SmartContractForm(
            instance=organization, datasets_by_organization={organization: []}
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
            instance=organization, datasets_by_organization={organization: [dataset]}
        )
        assert form.fields["scopes"].choices == []

    def test_generates_scope_choices_from_each_dataset(
        self, app: DjangoTestApp, organization: Organization, dataset: Dataset
    ) -> None:
        form = SmartContractForm(
            instance=organization, datasets_by_organization={organization: [dataset]}
        )

        assert set(form.fields["scopes"].choices) == {
            ("test_dataset_getall", "test_dataset_getall"),
            ("test_dataset_search", "test_dataset_search"),
            ("test_dataset_select", "test_dataset_select"),
        }


class TestAgreementUploadForm:
    def test_not_valid_when_uploading_file_other_than_adoc(self) -> None:
        uploaded_file = SimpleUploadedFile("bad_file.md", b"md file content")
        form = AgreementUploadForm(files={"file": uploaded_file})

        assert form.is_valid() is False
        assert form.errors == {"file": ["Dokumentas turi būti adoc formato."]}

    def test_not_valid_when_uploading_unsigned_adoc(self) -> None:
        file_path = (
            "tests/smart_contracts/files/test_contracts/sutartis_not_signed.adoc"
        )
        with open(file_path, "rb") as f:
            uploaded_file = SimpleUploadedFile("sutartis_not_signed.adoc", f.read())

        form = AgreementUploadForm(files={"file": uploaded_file})
        assert form.is_valid() is False
        assert form.errors == {"file": ["Įkelta sutartis nepasirašyta."]}
