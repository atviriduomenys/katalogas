from __future__ import annotations

import hashlib
import zipfile
from datetime import datetime
from typing import Optional

from vitrina.helpers import Monthly


def generate_checksum(data: str | bytes, algorithm: str = "sha256") -> str:
    hash_func = getattr(hashlib, algorithm)()
    if isinstance(data, str):
        data = data.encode("utf-8")
    hash_func.update(data)
    return hash_func.hexdigest()


def get_pdf_path_in_adoc(adoc_archive: zipfile.ZipFile) -> str | None:
    for file in adoc_archive.filelist:
        if file.filename.endswith(".pdf") and "/" not in file.filename:
            return file.filename
    return None


def format_lithuanian_datetime(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now()
    return f"{dt.year} m. {Monthly.titles[dt.month]} {dt.day} d."
