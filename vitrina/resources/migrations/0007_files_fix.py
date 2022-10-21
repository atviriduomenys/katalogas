import io
import mimetypes
import tempfile
import zipfile
from concurrent.futures import FIRST_EXCEPTION
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait
from typing import NamedTuple

import requests

import django.db.models.deletion
from django.db import migrations, models


class _Result(NamedTuple):
    dist: models.Model  # DatasetDistribution
    format: str


def fix_type_field_for_files(apps, schema_editor):
    Dist = apps.get_model("vitrina_resources", "DatasetDistribution")
    Format = apps.get_model("vitrina_resources", "Format")

    formats = {
        f.extension: f
        for f in Format.objects.all()
    }

    client = requests.Session()

    with ThreadPoolExecutor(100) as executor:
        futures = []
        for dist in Dist.objects.all():
            format = _detect_format(formats, executor, client, dist)
            if isinstance(format, Future):
                futures.append(format)
            else:
                _set_format(formats, dist, format)

        futures, _ = wait(futures, return_when=FIRST_EXCEPTION)
        for future in futures:
            res: _Result = future.result()
            if res:
                _set_format(formats, res.dist, res.format)


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
}


def _detect_format(
    formats: dict[str, models.Model],
    executor: ThreadPoolExecutor,
    client: requests.Session,
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
    if not dist.url:
        return

    # Before reading url, then to guess mime type first.
    format = _detect_from_name(dist.url)
    if format:
        return format

    # Try to detect format from response content type
    return executor.submit(_detect_url_format, client, dist)


def _detect_url_format(
    client: requests.Session,
    dist: models.Model,
) -> _Result | None:
    try:
        resp = client.get(dist.url, stream=True, timeout=1)
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
            return _Result(dist, format)


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
            # TODO: format = _detect_zip_format()
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


class Migration(migrations.Migration):

    dependencies = [
        ('vitrina_resources', '0006_region_municipality'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetdistribution',
            name='filename',
            field=models.FileField(blank=True,
                                   help_text='Atvirų duomenų katalogas nėra skirtas duomenų talpinimui'
                                             ' ir įprastinių atveju duomenys turėtu būti talpinami'
                                             ' atvirų duomenų Saugykloje ar kitoje vietoje, pateikiant'
                                             ' tiesioginę duomenų atsisiuntimo nuorodą. Tačiau nedidelės'
                                             ' apimties (iki 5Mb) duomenų failus, galima talpinti ir kataloge.',
                                   max_length=255, null=True, upload_to='data/', verbose_name='Duomenų failas'),
        ),
        migrations.RenameField(
            model_name='datasetdistribution',
            old_name='filename',
            new_name='file',
        ),
        migrations.AlterField(
            model_name='datasetdistribution',
            name='url_format',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='vitrina_resources.format', verbose_name='Šaltinio formatas'),
        ),
        migrations.RenameField(
            model_name='datasetdistribution',
            old_name='url_format',
            new_name='format',
        ),
        migrations.RunPython(fix_type_field_for_files)
    ]
