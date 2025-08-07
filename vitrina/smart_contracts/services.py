import json
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO
from pathlib import Path

import markdown
from jinja2 import Template
from pdfminer.high_level import extract_text
from weasyprint import HTML

from vitrina.smart_contracts.exceptions import InvalidAdocError
from vitrina.smart_contracts.utils import (
    generate_pdf_checksum,
    get_pdf_path_in_adoc,
    generate_checksum,
)

SIGNATURE_FILE_PATH = "META-INF/signatures/signatures0.xml"
MANIFEST_FILE_PATH = "META-INF/manifest.xml"
TEMP_PDF_PATH = "/tmp/_extracted_temp.pdf"

NAMESPACE_URI = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
MANIFEST_NAMESPACE = {"manifest": NAMESPACE_URI}

ATTR_FULL_PATH = f"{{{NAMESPACE_URI}}}full-path"
MANIFEST_FILE_ENTRY_TAG = "manifest:file-entry"


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


def is_checksum_valid(adoc_path: str, expected_checksum: str) -> bool:
    try:
        with zipfile.ZipFile(adoc_path, "r") as adoc_archive:
            pdf_path = get_pdf_path_in_adoc(adoc_archive)

            with adoc_archive.open(pdf_path) as pdf_file, open(
                TEMP_PDF_PATH, "wb"
            ) as out_file:
                out_file.write(pdf_file.read())

        actual_checksum = generate_pdf_checksum(TEMP_PDF_PATH)
        return actual_checksum == expected_checksum.lower()

    except (zipfile.BadZipFile, ET.ParseError, KeyError) as error:
        raise InvalidAdocError(f"Invalid ADOC file: {error}") from error
    finally:
        if os.path.exists(TEMP_PDF_PATH):
            os.remove(TEMP_PDF_PATH)


def generate_contract(
    template_path: str, odrl_data: dict, output: str | BytesIO
) -> None:
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
