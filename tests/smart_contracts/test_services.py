import pytest

from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.services import (
    extract_elements_from_adoc,
    has_valid_signature,
    is_checksum_valid,
)


CONTRACT_CHECKSUM = "cde4cc5c84554e7975355b6e27b003917355fb150acdd958786bdcca274a7d94"

SCOPES_REGEX = r"\buapi:/\S+"


def test_has_valid_signature_success():
    assert has_valid_signature("tests/smart_contracts/files/test_contracts/sutartis_signed.adoc")


def test_has_valid_signature_not_signed_adoc():
    assert not has_valid_signature(
        "tests/smart_contracts/files/test_contracts/sutartis_not_signed.adoc"
    )


def test_has_valid_signature_invalid_adoc():
    with pytest.raises(
        InvalidAdocError, match=r"Invalid ADOC file:.*META-INF/manifest\.xml"
    ):
        has_valid_signature("tests/smart_contracts/files/test_contracts/sutartis_no_manifest_file.adoc")


def test_is_checksum_valid_success():
    assert is_checksum_valid(
        "tests/smart_contracts/files/test_contracts/sutartis_signed.adoc",
        CONTRACT_CHECKSUM,
    )


def test_is_checksum_valid_added_extra_scope():
    assert not is_checksum_valid(
        "tests/smart_contracts/files/test_contracts/sutartis_signed_extra_scope.adoc",
        CONTRACT_CHECKSUM,
    )


def test_is_checksum_valid_same_contract_different_pdf_name():
    assert is_checksum_valid(
        "tests/smart_contracts/files/test_contracts/sutartis_signed_renamed.adoc",
        CONTRACT_CHECKSUM,
    )


def test_is_checksum_valid_missing_pdf_in_adoc():
    with pytest.raises(InvalidAdocError, match="Invalid ADOC file: no pdf file found"):
        is_checksum_valid(
            "tests/smart_contracts/files/test_contracts/sutartis_no_pdf_file.adoc",
            CONTRACT_CHECKSUM,
        )


def test_extract_elements_from_adoc():
    expected_scopes = [
        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
    ]
    assert (
        extract_elements_from_adoc("tests/smart_contracts/files/test_contracts/sutartis_signed.adoc", SCOPES_REGEX)
        == expected_scopes
    )


def test_extract_scopes_from_adoc_not_supported_file():
    with pytest.raises(
        InvalidAdocError, match="Invalid ADOC file: File is not a zip file"
    ):
        extract_elements_from_adoc("tests/smart_contracts/files/test_contracts/sutartis_valid.pdf", SCOPES_REGEX)
