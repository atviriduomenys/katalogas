from pathlib import Path

import pytest
import zipfile
from lxml import etree
from cryptography import x509

from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.services import (
    extract_elements_from_adoc,
    get_pdf_checksum_from_adoc,
    extract_signatures_from_adoc,
    extract_signers_certificate,
    get_signer_full_name_from_certificate,
    get_signers_from_adoc,
)
from tests.smart_contracts.constants import SIGNER1_FULL_NAME, SIGNER2_FULL_NAME


CONTRACT_CHECKSUM = "b5e8a02c5de0fab1da0564c9c7a9cbb5b9fe1b80826a2fd8705a4e4db3bae695"

SCOPES_REGEX = r"\buapi:/\S+"

test_contracts_dir = Path(__file__).parent / "files" / "test_contracts"


def test_is_checksum_valid_success(agreement_one_signer: Path):
    assert get_pdf_checksum_from_adoc(str(agreement_one_signer)) == CONTRACT_CHECKSUM


def test_is_checksum_valid_added_extra_scope():
    assert (
        not get_pdf_checksum_from_adoc(str(test_contracts_dir / "sutartis_signed_extra_scope.adoc"))
        == CONTRACT_CHECKSUM
    )


def test_is_checksum_valid_missing_pdf_in_adoc(agreement_no_pdf: Path):
    with pytest.raises(InvalidAdocError, match="Blogas ADOC failas: Nerastas PDF failas."):
        get_pdf_checksum_from_adoc(str(agreement_no_pdf))


def test_extract_elements_from_adoc(agreement_one_signer: Path):
    expected_scopes = [
        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getall",
        "uapi:/datasets/gov/rc/ar/ws/Country/@resident/:getone",
    ]
    assert extract_elements_from_adoc(str(agreement_one_signer), SCOPES_REGEX) == expected_scopes


def test_extract_scopes_from_adoc_not_supported_file(agreement_pdf: Path):
    with pytest.raises(InvalidAdocError, match="Invalid ADOC file: File is not a zip file"):
        extract_elements_from_adoc(str(agreement_pdf), SCOPES_REGEX)


def test_extract_sigatures_from_adoc(
    agreement_two_signers: Path, signature1: etree._Element, signature2: etree._Element
):
    with zipfile.ZipFile(agreement_two_signers) as zip_file:
        signatures = extract_signatures_from_adoc(zip_file)
    assert len(signatures) == 2
    assert etree.tostring(signatures[0], method="c14n") == etree.tostring(signature1, method="c14n")
    assert etree.tostring(signatures[1], method="c14n") == etree.tostring(signature2, method="c14n")


def test_extract_signers_certificate(signature1: etree._Element, certificate: x509.Certificate):
    assert extract_signers_certificate(signature1) == certificate


def test_extract_signers_certificate_bad_certificate(agreement_bad_certificate: Path):
    with zipfile.ZipFile(agreement_bad_certificate) as zip_file:
        signatures = extract_signatures_from_adoc(zip_file)
        with pytest.raises(InvalidAdocError, match="Netinkamas parašo sertifikatas"):
            extract_signers_certificate(signatures[0])


def test_get_signer_from_certificate(certificate: x509.Certificate):
    signer = get_signer_full_name_from_certificate(certificate)
    assert signer == SIGNER1_FULL_NAME


def test_get_signer_from_certificate_no_first_name(certificate_no_first_name: x509.Certificate):
    with pytest.raises(InvalidAdocError, match="Paraše trūksta pasirašiusio asmens vardo ir/ar pavardės."):
        get_signer_full_name_from_certificate(certificate_no_first_name)


def test_get_signers_from_adoc(agreement_two_signers: Path):
    with zipfile.ZipFile(agreement_two_signers) as zip_file:
        signers = get_signers_from_adoc(zip_file)

    assert len(signers) == 2
    assert signers[0] == SIGNER1_FULL_NAME
    assert signers[1] == SIGNER2_FULL_NAME
