import os
import io
import mimetypes
import tempfile
import zipfile
from typer import run, Option
from concurrent.futures import FIRST_EXCEPTION
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from typing import NamedTuple

import django
from django.db import migrations, models
from django.apps import apps
import requests
from requests_cache import CachedSession


class _Result(NamedTuple):
    dist: models.Model  # DatasetDistribution
    format: str


def main():
    Dist = apps.get_model("vitrina_resources", "DatasetDistribution")
    Format = apps.get_model("vitrina_resources", "Format")

    formats = {
        f.extension: f
        for f in Format.objects.all()
    }

    client = CachedSession('demo_cache')


    dists_amount = len(Dist.objects.all())
    futures = []
    for dist in Dist.objects.all():
        format = _detect_format(formats, client, dist)
        if format:
            _set_format(formats, dist, format)



_mime_types = {
    'text/html': 'HTML',
    'application/xhtml+xml': 'HTML',
    'application/pdf': 'PDF',
    'application/vnd.ms-excel': 'XLSX',
    'application/zip': 'ZIP',
    'text/csv': 'CSV',
    'application/x-download': 'URL',
    'application/json': 'JSON',
    'text/xml': 'XML',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    'application/xml': 'XML',
    'application/rdf+xml': 'RDF',
    'text/plain': 'URL',
    'application/geo+json': 'JSON',
    'multipart/x-zip': 'ZIP',
    'application/octet-stream': 'SHAPE',
    'video/mp4': 'URL',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOC',
    'application/msword': 'DOC',
    'application/x-zip-compressed': 'ZIP'
}


def _detect_format(
    formats: dict[str, models.Model],
    client: CachedSession,
    dist: models.Model,
) -> str | None:

    # If format is set, we are good.
    if dist.format:
        return

    # If dist is a file, detect from file extension.
    if dist.file:
        format = _detect_from_name(str(dist.file))
        if format:
            return format

    # If dist is not a file and not a url, what is it then?
    if not dist.download_url:
        return

    # Before reading url, then to guess mime type first.
    format = _detect_from_name(dist.download_url)
    if format:
        return format

    # Try to detect format from response content type
    return _detect_url_format(client, dist)


def _detect_url_format(
    client: CachedSession,
    dist: models.Model,
) -> str | None:
    try:
        resp = client.get(dist.download_url, stream=True, timeout=1)
    except requests.RequestException:
        return

    if not resp.ok:
        return

    content_type = resp.headers.get('content-type')
    if ';' in content_type:
        content_type = content_type.split(';', 1)[0]

    format = _mime_types[content_type]

    if format == 'ZIP':
        with tempfile.NamedTemporaryFile() as f:
            for chunk in resp.iter_content():
                f.write(chunk)
            f.seek(0)
            format = _detect_zip_format(f),
            return format


def _detect_zip_format(f: io.BytesIO) -> str:
    with zipfile.ZipFile(f) as zf:
        for name in zf.namelist():
            format = _detect_from_name(name)
            if format:
                return format
    return 'URL'


def _detect_from_name(name: str) -> str | None:
    mime_type, _ = mimetypes.guess_type(name)
    if mime_type:
        format = _mime_types[mime_type]
        if format == 'ZIP':
            # TODO: format = _detect_zip_format(), connection.schema_editor
            return 'URL'
        return format


def _set_format(
    formats: dict[str, models.Model],
    dist: models.Model,
    format: str | None,
) -> None:
    if format:
        dist.format = formats[format]
        dist.save(update_fields=['format'])

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vitrina.settings")
    django.setup()
    run(main)