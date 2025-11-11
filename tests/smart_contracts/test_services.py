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


def test_has_valid_signature_success():
    assert has_valid_signature(str(test_contracts_dir / "sutartis_signed.adoc"))


def test_has_valid_signature_not_signed_adoc():
    assert not has_valid_signature(str(test_contracts_dir / "sutartis_not_signed.adoc"))


def test_has_valid_signature_invalid_adoc():
    with pytest.raises(
        InvalidAdocError, match=r"Invalid ADOC file:.*META-INF/manifest\.xml"
    ):
        has_valid_signature(str(test_contracts_dir / "sutartis_no_manifest_file.adoc"))


def test_is_checksum_valid_success():
    assert get_pdf_checksum_from_adoc(str(test_contracts_dir / "sutartis_signed.adoc")) == CONTRACT_CHECKSUM


def test_is_checksum_valid_added_extra_scope():
    assert not get_pdf_checksum_from_adoc(str(test_contracts_dir / "sutartis_signed_extra_scope.adoc")) == CONTRACT_CHECKSUM

def test_is_checksum_valid_missing_pdf_in_adoc():
    with pytest.raises(InvalidAdocError, match="Invalid ADOC file: no pdf file found"):
        get_pdf_checksum_from_adoc(str(test_contracts_dir / "sutartis_no_pdf_file.adoc"))


def test_extract_elements_from_adoc():
    expected_scopes = [
        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
    ]
    assert (
        extract_elements_from_adoc(
            str(test_contracts_dir / "sutartis_signed.adoc"), SCOPES_REGEX
        )
        == expected_scopes
    )


def test_extract_scopes_from_adoc_not_supported_file():
    with pytest.raises(
        InvalidAdocError, match="Invalid ADOC file: File is not a zip file"
    ):
        extract_elements_from_adoc(
            str(test_contracts_dir / "sutartis_valid.pdf"), SCOPES_REGEX
        )
