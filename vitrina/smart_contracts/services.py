import json
import os
import re
import xml.etree.ElementTree as ET
from lxml import etree
import zipfile
from io import BytesIO
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from base64 import b64decode
import binascii
import logging


import markdown
from jinja2 import Template
from pdfminer.high_level import extract_text
# from weasyprint import HTML

from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.utils import (
    get_pdf_path_in_adoc,
    generate_checksum,
)
from vitrina.users.models import User
from vitrina.smart_contracts.models import Agreement, AgreementStatuses
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger()

MANIFEST_FILE_PATH = "META-INF/manifest.xml"
TEMP_PDF_PATH = "/tmp/_extracted_temp.pdf"

SIGNATURES_DIR = "META-INF/signatures/"
SIGNATURE_NAMESPACES = {"ds": "http://www.w3.org/2000/09/xmldsig#", "xades": "http://uri.etsi.org/01903/v1.3.2#"}
SAFE_PARSER = etree.XMLParser(
    remove_blank_text=True,
    resolve_entities=False,
    no_network=True,
    huge_tree=False,
)
X509_CERTIFICATE_XPATH = ".//ds:KeyInfo/ds:X509Data/ds:X509Certificate"


def is_valid_adoc_structure(zip_file: zipfile.ZipFile) -> bool:
    names = zip_file.namelist()
    has_manifest = MANIFEST_FILE_PATH in names
    has_payload = any(name != "mimetype" and "/" not in name for name in names)
    return has_payload and has_manifest


def extract_signatures_from_adoc(zip_file: zipfile.ZipFile) -> list[etree._Element]:
    signature_xml_paths = [
        file_name
        for file_name in zip_file.namelist()
        if file_name.startswith(SIGNATURES_DIR) and file_name.lower().endswith(".xml") and not file_name.endswith("/")
    ]

    signatures = []

    for file_name in signature_xml_paths:
        with zip_file.open(file_name) as xml_file:
            try:
                xml_tree = etree.parse(xml_file, SAFE_PARSER)
            except etree.XMLSyntaxError:
                logger.info(f"Error while parsing XML file {xml_file}")
                continue

        if (signature := xml_tree.find(".//ds:Signature", namespaces=SIGNATURE_NAMESPACES)) is not None:
            signatures.append(signature)

    return signatures


def extract_signers_certificate(signature: etree._Element) -> x509.Certificate:
    certificate = signature.find(X509_CERTIFICATE_XPATH, namespaces=SIGNATURE_NAMESPACES)
    if certificate is None or not certificate.text:
        raise InvalidAdocError(_("Nepavyko rasti parašo sertifikato."))
    b64 = "".join(certificate.text.split())
    try:
        return x509.load_der_x509_certificate(b64decode(b64))
    except (binascii.Error, ValueError) as error:
        raise InvalidAdocError(_("Netinkamas parašo sertifikatas.")) from error


def get_signer_full_name_from_certificate(certificate: x509.Certificate) -> str:
    subject = certificate.subject

    def get_value(oid: NameOID) -> str | None:
        attributes = subject.get_attributes_for_oid(oid)
        return " ".join(attribute.value.strip() for attribute in attributes) if attributes else None

    first_name = get_value(NameOID.GIVEN_NAME)
    last_name = get_value(NameOID.SURNAME)

    if not all([first_name, last_name]):
        raise InvalidAdocError(_("Paraše trūksta pasirašiusio asmens vardo ir/ar pavardės."))

    return f"{first_name} {last_name}"


def get_signers_from_adoc(zip_file: zipfile.ZipFile) -> list[str]:
    signers = []
    for signature in extract_signatures_from_adoc(zip_file):
        certificate = extract_signers_certificate(signature)
        signers.append(get_signer_full_name_from_certificate(certificate))

    return signers


def num_of_adoc_root_files(zip_file: zipfile.ZipFile) -> int:
    return len([file for file in zip_file.filelist if "/" not in file.filename and file.filename != "mimetype"])


def validate_adoc(zip_file: zipfile.ZipFile, checksum: str) -> tuple[bool, str]:
    if not is_valid_adoc_structure(zip_file):
        raise InvalidAdocError("Neteisingas ADOC formatas.")
    if num_of_adoc_root_files(zip_file) > 1:
        raise InvalidAdocError(_("Rastas daugiau nei vienas pasirašytas dokumentas."))
    if not (pdf_path := get_pdf_path_in_adoc(zip_file)):
        raise InvalidAdocError(_("Nerastas PDF dokumentas."))
    with zip_file.open(pdf_path) as pdf_file:
        pdf_bytes = pdf_file.read()
    if generate_checksum(pdf_bytes) != checksum:
        raise InvalidAdocError(_("PDF dokumentas nesutampa su sutartyje esančiu PDF dokumentu."))


def validate_signatures(signers: list[str], agreement: Agreement) -> tuple[bool, str | None]:
    num_of_signers = len(signers)

    if num_of_signers == 0:
        return False, _("Įkelta sutartis nepasirašyta.")

    signers_to_find = [agreement.get_odrl_assignee_representative()]
    if agreement.status == AgreementStatuses.FORMED:
        if num_of_signers > 1:
            return False, _(
                "Įkelta sutartis pasirašyta daugiau nei 1 parašu. Gavėjas turėtų pasirašyti tik vienu parašu."
            )
    elif agreement.status == AgreementStatuses.INITIATED:
        if num_of_signers == 1:
            return False, _("Įkelta sutartis nepasirašyta teikėjo parašu.")
        if num_of_signers > 2:
            return False, _("Įkeltoje sutartyje rasti daugiau nei 2 parašai.")
        signers_to_find.append(agreement.get_odrl_assigner_representative())
    else:
        return False, _("Pasirašyti galima tik sutartis su būsenomis `{formed}` arba `{initiated}`.").format(
            formed=AgreementStatuses.FORMED, initiated=AgreementStatuses.INITIATED
        )

    if set(signers) != set(signers_to_find):
        return False, _(
            "Nesutampa pasirašiusių asmenų vardai ir pavardės. "
            "Reikalingi parašai: {expected}, ADOC rasti parašai: {found}."
        ).format(
            expected=signers_to_find,
            found=signers,
        )
    return True, None


def get_pdf_checksum_from_adoc(adoc_path: str) -> str:
    try:
        with zipfile.ZipFile(adoc_path) as adoc_archive:
            pdf_path = get_pdf_path_in_adoc(adoc_archive)

            if not pdf_path:
                raise InvalidAdocError(_("Nerastas PDF failas."))

            with adoc_archive.open(pdf_path) as pdf_file:
                pdf_bytes = pdf_file.read()

            return generate_checksum(pdf_bytes)

    except (zipfile.BadZipFile, InvalidAdocError) as error:
        raise InvalidAdocError(_("Blogas ADOC failas: {error}").format(error=error)) from error


def generate_contract(template_path: str, odrl_data: dict, output: str | BytesIO) -> None:
    json_checksum = generate_checksum(json.dumps(odrl_data, sort_keys=True))
    md_template = Path(template_path).read_text(encoding="utf-8")
    template_checksum = generate_checksum(md_template)
    template = Template(md_template)
    md_filled = template.render(
        odrl_data=odrl_data,
        json_checksum=json_checksum,
        template_checksum=template_checksum,
    )

    html_text = markdown.markdown(md_filled, extensions=["extra"])
    HTML(string=html_text).write_pdf(output)


def extract_elements_from_adoc(adoc_path: str, regex: str) -> list[str]:
    try:
        with zipfile.ZipFile(adoc_path, "r") as adoc_archive:
            pdf_path = get_pdf_path_in_adoc(adoc_archive)

            with adoc_archive.open(pdf_path) as pdf_file:
                with open(TEMP_PDF_PATH, "wb") as out_file:
                    out_file.write(pdf_file.read())

        text = extract_text(TEMP_PDF_PATH)
        compiled = re.compile(regex)
        return compiled.findall(text)

    except (zipfile.BadZipFile, ET.ParseError, KeyError) as error:
        raise InvalidAdocError(f"Invalid ADOC file: {error}") from error
    finally:
        if os.path.exists(TEMP_PDF_PATH):
            os.remove(TEMP_PDF_PATH)


def get_agreements(user: User) -> QuerySet[Agreement]:
    if not user.is_authenticated:
        return Agreement.objects.none()

    if user.is_staff or user.is_superuser:
        return Agreement.objects.all()

    represented_org_ids = user.represented_org_ids
    queryset = Agreement.objects.filter(Q(assignee_id__in=represented_org_ids) | Q(assigner_id__in=represented_org_ids))

    return queryset
