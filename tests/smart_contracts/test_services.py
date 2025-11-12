from pathlib import Path

import pytest

from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.services import (
    extract_elements_from_adoc,
    has_valid_signature,
    get_pdf_checksum_from_adoc,
)


CONTRACT_CHECKSUM = "b5e8a02c5de0fab1da0564c9c7a9cbb5b9fe1b80826a2fd8705a4e4db3bae695"

SCOPES_REGEX = r"\buapi:/\S+"

test_contracts_dir = Path(__file__).parent / "files" / "test_contracts"


def test_has_valid_signature_success(agreement_one_signer: Path):
    assert has_valid_signature(str(agreement_one_signer))


def test_has_valid_signature_not_signed_adoc(agreement_not_signed: Path):
    assert not has_valid_signature(str(agreement_not_signed))


def test_has_valid_signature_invalid_adoc(agreement_invalid: Path):
    with pytest.raises(
        InvalidAdocError, match=r"Invalid ADOC file:.*META-INF/manifest\.xml"
    ):
        has_valid_signature(str(agreement_invalid))


def test_is_checksum_valid_success(agreement_one_signer: Path):
    assert get_pdf_checksum_from_adoc(str(agreement_one_signer)) == CONTRACT_CHECKSUM


def test_is_checksum_valid_added_extra_scope():
    assert not get_pdf_checksum_from_adoc(str(test_contracts_dir / "sutartis_signed_extra_scope.adoc")) == CONTRACT_CHECKSUM

def test_is_checksum_valid_missing_pdf_in_adoc(agreement_no_pdf: Path):
    with pytest.raises(InvalidAdocError, match="Invalid ADOC file: No PDF file found"):
        get_pdf_checksum_from_adoc(str(agreement_no_pdf))


def test_extract_elements_from_adoc(agreement_one_signer: Path):
    expected_scopes = [
        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
    ]
    assert (
        extract_elements_from_adoc(
            str(agreement_one_signer), SCOPES_REGEX
        )
        == expected_scopes
    )


def test_extract_scopes_from_adoc_not_supported_file(agreement_pdf: Path):
    with pytest.raises(
        InvalidAdocError, match="Invalid ADOC file: File is not a zip file"
    ):
        extract_elements_from_adoc(
            str(agreement_pdf), SCOPES_REGEX
        )
