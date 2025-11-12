import pytest
from pathlib import Path
from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.structure.factories import MetadataFactory

AGREEMENT_ONE_SIGNER = "agreement_one_signer.adoc"
AGREEMENT_TWO_SIGNERS = "agreement_two_signers.adoc"
AGREEMENT_INVALID = "agreement_no_manifest.adoc"
AGREEMENT_BAD_CERTIFICATE = "agreement_bad_certificate.adoc"
AGREEMENT_MODIFIED = "agreement_modified.adoc"
AGREEMENT_NO_PDF = "agreement_no_pdf.adoc"
AGREEMENT_TWO_FILES = "agreement_two_files.adoc"
AGREEMENT_NOT_SIGNED = "agreement_not_signed.adoc"
AGREEMENT_PDF = "agreement.pdf"

@pytest.fixture
def organization() -> Organization:
    return OrganizationFactory()


@pytest.fixture
def dataset(organization: Organization) -> Dataset:
    dataset = DatasetFactory(organization=organization)
    MetadataFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        dataset=dataset,
        name="test/dataset",
    )

    return dataset

@pytest.fixture
def agreements_dir() -> Path:
    return Path(__file__).resolve().parent / "files" / "test_contracts"

@pytest.fixture
def agreement_one_signer(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_ONE_SIGNER

@pytest.fixture
def agreement_two_signers(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_TWO_SIGNERS

@pytest.fixture
def agreement_invalid(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_INVALID

@pytest.fixture
def agreement_bad_certificate(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_BAD_CERTIFICATE

@pytest.fixture
def agreement_modified(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_MODIFIED

@pytest.fixture
def agreement_no_pdf(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_NO_PDF

@pytest.fixture
def agreement_two_files(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_TWO_FILES

@pytest.fixture
def agreement_not_signed(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_NOT_SIGNED

@pytest.fixture
def agreement_pdf(agreements_dir: Path) -> Path:
    return agreements_dir / AGREEMENT_PDF
