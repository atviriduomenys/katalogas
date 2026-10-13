import logging
import time
from datetime import datetime
from urllib.parse import urlparse

import reversion
from celery import shared_task
from django.utils import timezone
from rest_framework import serializers

from vitrina.structure.services import get_data_from_spinta
from vitrina.resources.models import DatasetDistribution, FormatName

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL_HOURS = 24
BATCH_SIZE = 10
BATCH_DELAY_SECONDS = 2


class SpintaChangeSerializer(serializers.Serializer):
    _created = serializers.DateTimeField()


@shared_task
def update_spinta_distribution_dates() -> None:
    distributions = list(
        DatasetDistribution.objects.filter(format__extension=FormatName.UAPI)
        .select_related("dataset__frequency")
        .exclude(dataset__isnull=True)
    )

    now = timezone.now()
    to_check = []
    total = 0

    for distribution in distributions:
        total += 1
        frequency_hours = _get_frequency_hours(distribution)
        if distribution.data_last_updated:
            next_check = distribution.data_last_updated + timezone.timedelta(hours=frequency_hours)
            if next_check > now:
                continue
        to_check.append(distribution)

    skipped = total - len(to_check)
    if not to_check:
        logger.info("No SPINTA distributions due for update check (%d skipped).", skipped)
        return

    logger.info("Checking %d SPINTA distributions for data updates (%d skipped).", len(to_check), skipped)

    updated = []
    for i, distribution in enumerate(to_check):
        if i > 0 and i % BATCH_SIZE == 0:
            time.sleep(BATCH_DELAY_SECONDS)

        try:
            spinta_modified = _fetch_spinta_last_modified(distribution)
            if spinta_modified and (
                not distribution.data_last_updated or spinta_modified > distribution.data_last_updated
            ):
                distribution.data_last_updated = spinta_modified
                updated.append(distribution)
        except Exception:
            logger.exception("Failed to check SPINTA data for distribution %d", distribution.pk)

    if updated:
        for distribution in updated:
            with reversion.create_revision():
                distribution.save(update_fields=["data_last_updated"])
                reversion.set_comment("Updated data_last_updated from SPINTA")
        logger.info("Updated data_last_updated for %d distributions.", len(updated))
    else:
        logger.info("No SPINTA distributions had newer data.")


def _get_frequency_hours(distribution: DatasetDistribution) -> int:
    if distribution.dataset and distribution.dataset.frequency:
        hours = distribution.dataset.frequency.hours
        if hours and hours > 0:
            return hours
    return DEFAULT_CHECK_INTERVAL_HOURS


def _fetch_spinta_last_modified(distribution: DatasetDistribution) -> datetime | None:
    if not distribution.dataset:
        logger.debug("Distribution %d has no dataset, skipping.", distribution.pk)
        return None

    model_names = _model_names_from_url(distribution.download_url) or [
        model.full_name for model in distribution.dataset.model_set.all()
    ]
    if not model_names:
        logger.debug("Distribution %d has no SPINTA models, skipping.", distribution.pk)
        return None

    latest: datetime | None = None
    for model_name in model_names:
        latest_model_datetime = _fetch_model_last_modified(model_name, distribution.pk)
        if latest_model_datetime and (latest is None or latest_model_datetime > latest):
            latest = latest_model_datetime
    return latest


def _model_names_from_url(url: str | None) -> list[str]:
    path = urlparse(url or "").path.strip("/").removesuffix("/:ns")
    if not path.startswith("datasets/"):
        return []
    if path.rsplit("/", 1)[-1][:1].isupper():
        return [path]
    data = get_data_from_spinta(f"{path}/:ns", timeout=15)
    return [item["name"] for item in data.get("_data", []) if not item["name"].endswith("/:ns")]


def _fetch_model_last_modified(model_full_name: str, distribution_pk: int) -> datetime | None:
    data = get_data_from_spinta(model_full_name, ":changes/-1/", timeout=15)

    if not data:
        return None

    if "errors" in data:
        logger.warning(
            "SPINTA returned errors for distribution %d model %s: %s",
            distribution_pk,
            model_full_name,
            data["errors"],
        )
        return None

    items = data.get("_data", [])
    if not items:
        logger.debug(
            "Distribution %d model %s SPINTA response has no _data items, skipping.",
            distribution_pk,
            model_full_name,
        )
        return None

    serializer = SpintaChangeSerializer(data=items[0])
    if not serializer.is_valid():
        logger.warning(
            "Invalid SPINTA change entry for distribution %d model %s: %s",
            distribution_pk,
            model_full_name,
            serializer.errors,
        )
        return None

    return serializer.validated_data["_created"]
