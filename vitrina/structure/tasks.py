from celery import shared_task
from .models import DsaValidationEntry
from spinta.core.context import create_context
from spinta.cli.config import check
from spinta.core.enums import Mode
from types import SimpleNamespace


@shared_task
def validate_dsa_task(dsa_id):
    dsa_instance = DsaValidationEntry.objects.get(pk=dsa_id)
    ctx = SimpleNamespace(obj=create_context("cli"))
    try:
        check(ctx, manifests=[str(dsa_instance.dsa_file.path)], mode=Mode("internal"))
        dsa_instance.validation_status = "valid"
        dsa_instance.error_message = ""
    except Exception as error:
        dsa_instance.validation_status = "invalid"
        dsa_instance.error_message = str(error)
    dsa_instance.save()
