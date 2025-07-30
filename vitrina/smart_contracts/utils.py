from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from typing import Optional

from pdfminer.high_level import extract_text

from vitrina.helpers import Monthly
from vitrina.smart_contracts.exceptions import InvalidAdocError

MANIFEST_FILE_PATH = "META-INF/manifest.xml"

NAMESPACE_URI = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
MANIFEST_NAMESPACE = {"manifest": NAMESPACE_URI}
PDF_MEDIA_TYPE = "application/pdf"

ATTR_FULL_PATH = f"{{{NAMESPACE_URI}}}full-path"
ATTR_MEDIA_TYPE = f"{{{NAMESPACE_URI}}}media-type"
MANIFEST_FILE_ENTRY_TAG = "manifest:file-entry"


def generate_checksum(data: str | bytes, algorithm: str = "sha256") -> str:
    hash_func = getattr(hashlib, algorithm)()
    if isinstance(data, str):
        data = data.encode("utf-8")
    hash_func.update(data)
    return hash_func.hexdigest()


def generate_pdf_checksum(pdf_path: str, algorithm: str = "sha256") -> str:
    text = extract_text(pdf_path)
    return generate_checksum(text, algorithm)


def get_pdf_path_in_adoc(adoc_archive: zipfile.ZipFile) -> str:
    with adoc_archive.open(MANIFEST_FILE_PATH) as manifest_file:
        tree = ET.parse(manifest_file)
        root = tree.getroot()
        file_entries = root.findall(MANIFEST_FILE_ENTRY_TAG, MANIFEST_NAMESPACE)

        for entry in file_entries:
            full_path = entry.attrib.get(ATTR_FULL_PATH)
            media_type = entry.attrib.get(ATTR_MEDIA_TYPE)

            if media_type == PDF_MEDIA_TYPE and full_path in adoc_archive.namelist():
                return full_path
    raise InvalidAdocError("Invalid ADOC file: no pdf file found")


def format_lithuanian_datetime(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now()
    return f"{dt.year} m. {Monthly.titles[dt.month]} {dt.day} d."