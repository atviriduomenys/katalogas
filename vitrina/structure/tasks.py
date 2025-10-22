import contextlib
import io

from celery import shared_task
from .models import ManifestValidationEntry
from spinta.core.context import create_context
from spinta.cli.config import check
from spinta.core.enums import Mode
from types import SimpleNamespace
from uuid import UUID


@shared_task
def validate_manifest_task(manifest_id: UUID) -> None:
    manifest = ManifestValidationEntry.objects.get(pk=manifest_id)
    ctx = SimpleNamespace(obj=create_context("cli"))

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            check(ctx, manifests=[str(manifest.manifest_file.path)], mode=Mode("internal"))
            manifest.validation_status = "valid"
            manifest.error_message = ""
        except Exception as e:
            manifest.validation_status = "invalid"
            manifest.error_message = f"Exception: {e}"

    logs = buf.getvalue()
    if "Context:" in logs or "Total errors" in logs:
        manifest.validation_status = "invalid"
        manifest.error_message = logs

    manifest.save()
