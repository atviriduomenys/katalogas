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
from weasyprint import HTML
from dataclasses import dataclass

from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.utils import (
    get_pdf_path_in_adoc,
    generate_checksum,
)
from vitrina.users.models import User
from vitrina.smart_contracts.models import Agreement
from vitrina.projects.models import Project
from django.db.models import Q, QuerySet
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger()

SIGNATURE_FILE_PATH = "META-INF/signatures/signatures0.xml"
MANIFEST_FILE_PATH = "META-INF/manifest.xml"
TEMP_PDF_PATH = "/tmp/_extracted_temp.pdf"

NAMESPACE_URI = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
MANIFEST_NAMESPACE = {"manifest": NAMESPACE_URI}

ATTR_FULL_PATH = f"{{{NAMESPACE_URI}}}full-path"
MANIFEST_FILE_ENTRY_TAG = "manifest:file-entry"

SIGNATURES_DIR = "META-INF/signatures/"
SIGNATURE_NAMESPACES = {"ds": "http://www.w3.org/2000/09/xmldsig#", "xades": "http://uri.etsi.org/01903/v1.3.2#"}
SAFE_PARSER = etree.XMLParser(
    remove_blank_text=True,
    resolve_entities=False,
    no_network=True,
    huge_tree=False,
)
X509_CERTIFICATE_XPATH = ".//ds:KeyInfo/ds:X509Data/ds:X509Certificate"


@dataclass
class Signer:
    first_name: str
    last_name: str

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


def is_valid_adoc(zip_file: zipfile.ZipFile) -> bool:
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


def get_signer_from_certificate(certificate: x509.Certificate) -> Signer:
    subject = certificate.subject

    def get_value(oid: NameOID) -> str | None:
        attributes = subject.get_attributes_for_oid(oid)
        return " ".join(attribute.value.strip() for attribute in attributes) if attributes else None

    first_name = get_value(NameOID.GIVEN_NAME)
    last_name = get_value(NameOID.SURNAME)

    if not all([first_name, last_name]):
        raise InvalidAdocError(_("Paraše trūksta pasirašiusio asmens vardo ir/ar pavardės."))

    return Signer(first_name=first_name, last_name=last_name)


def get_signers_from_adoc(zip_file: zipfile.ZipFile) -> list[Signer]:
    signers = []
    for signature in extract_signatures_from_adoc(zip_file):
        certificate = extract_signers_certificate(signature)
        signers.append(get_signer_from_certificate(certificate))

    return signers


def num_of_adoc_root_files(zip_file: zipfile.ZipFile) -> int:
    return len([file for file in zip_file.filelist if "/" not in file.filename and file.filename != "mimetype"])


def has_valid_signature(adoc_path: str) -> bool:
    try:
        with zipfile.ZipFile(adoc_path, "r") as adoc_archive:
            with adoc_archive.open(MANIFEST_FILE_PATH) as manifest_file:
                tree = ET.parse(manifest_file)
                root = tree.getroot()
                file_entries = root.findall(MANIFEST_FILE_ENTRY_TAG, MANIFEST_NAMESPACE)

                for entry in file_entries:
                    full_path = entry.attrib.get(ATTR_FULL_PATH)
                    if full_path == SIGNATURE_FILE_PATH:
                        return True
        return False
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as error:
        raise InvalidAdocError(f"Invalid ADOC file: {error}") from error


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


def get_agreements(user: User) -> QuerySet["Agreement"]:
    if not user.is_authenticated:
        return Agreement.objects.none()

    if user.is_staff or user.is_superuser:
        return Agreement.objects.all()

    represented_org_ids = user.represented_org_ids
    queryset = Agreement.objects.filter(Q(assignee_id__in=represented_org_ids) | Q(assigner_id__in=represented_org_ids))

    return queryset


def can_view_agreements(user: User | AnonymousUser, project: Project) -> bool:
    if not user.is_authenticated:
        return False

    represented_org_ids = user.represented_org_ids

    if user.is_staff or user.is_superuser:
        return True

    if project.organization and project.organization.id in represented_org_ids:
        return True

    return project.agreements.filter(assigner_id__in=represented_org_ids).exists()


def can_view_agreement(user: User, agreement: Agreement) -> bool:
    return get_agreements(user).filter(pk=agreement.pk).exists()


def can_create_agreements(user: User, project: Project) -> bool:
    if project.organization:
        return project.organization == user.viisp_organization and user.is_representative_of(project.organization, True)

    return False


def can_upload_agreement_file(user: User, agreement: Agreement) -> bool:
    parties = [agreement.assignee, agreement.assigner]

    return any(user.viisp_organization == party and user.is_representative_of(party, True) for party in parties)
