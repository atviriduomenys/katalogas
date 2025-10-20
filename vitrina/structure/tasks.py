from celery import shared_task
from .models import ManifestValidationEntry
from spinta.core.context import create_context
from spinta.cli.config import check
from spinta.core.enums import Mode
from types import SimpleNamespace
from uuid import UUID


@shared_task
def validate_manifest_task(manifest_id: UUID) -> None:
    manifest_instance = ManifestValidationEntry.objects.get(pk=manifest_id)
    ctx = SimpleNamespace(obj=create_context("cli"))
    try:
        check(ctx, manifests=[str(manifest_instance.dsa_file.path)], mode=Mode("internal"))
        manifest_instance.validation_status = "valid"
        manifest_instance.error_message = ""
    except Exception as error:
        manifest_instance.validation_status = "invalid"
        manifest_instance.error_message = str(error)
    manifest_instance.save()
