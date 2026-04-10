import logging
import time
from datetime import datetime

from celery import shared_task
from django.utils import timezone

from vitrina.resources.models import DatasetDistribution, FormatName

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL_HOURS = 24
BATCH_SIZE = 10
BATCH_DELAY_SECONDS = 2


@shared_task
def update_spinta_distribution_dates():
    distributions = list(
        DatasetDistribution.objects.filter(format__extension=FormatName.UAPI)
        .select_related("dataset__frequency")
        .exclude(dataset__isnull=True)
    )

    now = timezone.now()
    to_check = []
    total = 0

    for dist in distributions:
        total += 1
        frequency_hours = _get_frequency_hours(dist)
        if dist.data_last_updated:
            next_check = dist.data_last_updated + timezone.timedelta(hours=frequency_hours)
            if next_check > now:
                continue
        to_check.append(dist)

    skipped = total - len(to_check)
    if not to_check:
        logger.info("No SPINTA distributions due for update check (%d skipped).", skipped)
        return

    logger.info("Checking %d SPINTA distributions for data updates (%d skipped).", len(to_check), skipped)

    updated = []
    for i, dist in enumerate(to_check):
        if i > 0 and i % BATCH_SIZE == 0:
            time.sleep(BATCH_DELAY_SECONDS)

        try:
            spinta_modified = _fetch_spinta_last_modified(dist)
            if spinta_modified and (not dist.data_last_updated or spinta_modified > dist.data_last_updated):
                dist.data_last_updated = spinta_modified
                updated.append(dist)
        except Exception:
            logger.exception("Failed to check SPINTA data for distribution %d", dist.pk)

    if updated:
        DatasetDistribution.objects.bulk_update(updated, ["data_last_updated"], batch_size=100)
        logger.info("Updated data_last_updated for %d distributions.", len(updated))
    else:
        logger.info("No SPINTA distributions had newer data.")


def _get_frequency_hours(dist):
    if dist.dataset and dist.dataset.frequency:
        hours = dist.dataset.frequency.hours
        if hours and hours > 0:
            return hours
    return DEFAULT_CHECK_INTERVAL_HOURS


def _fetch_spinta_last_modified(dist):
    from vitrina.structure.services import get_data_from_spinta

    if not dist.dataset:
        logger.debug("Distribution %d has no dataset, skipping.", dist.pk)
        return None

    models = dist.dataset.model_set.all()
    if not models.exists():
        logger.debug("Distribution %d dataset has no models, skipping.", dist.pk)
        return None

    model = models.first()
    data = get_data_from_spinta(
        f"{model.full_name}/:changes/:format/json",
        query="select(_created)&limit(10000)",
        timeout=15,
    )

    if not data or "errors" in data:
        if data and "errors" in data:
            logger.warning(
                "SPINTA returned errors for distribution %d: %s",
                dist.pk,
                data["errors"],
            )
        return None

    items = data.get("_data", [])
    if not items:
        logger.debug("Distribution %d SPINTA response has no _data items, skipping.", dist.pk)
        return None

    created = items[-1].get("_created")
    if not created:
        logger.debug("Distribution %d SPINTA response has no _created field, skipping.", dist.pk)
        return None

    try:
        parsed = datetime.fromisoformat(created)
        if parsed.tzinfo is None:
            parsed = timezone.make_aware(parsed)
        return parsed
    except (ValueError, TypeError):
        logger.warning("Invalid _created format for distribution %d: %s", dist.pk, created)
        return None
