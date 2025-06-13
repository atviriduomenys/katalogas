import logging

from django_q.tasks import schedule
from django_q.models import Schedule
from django.conf import settings


logger = logging.getLogger(__name__)


def setup_remote_file_size_check_schedule() -> None:
    """Setup the periodic task for checking file sizes."""
    schedule_name = "check_remote_file_sizes"

    Schedule.objects.filter(name=schedule_name).delete()
    schedule(
        "vitrina.resources.tasks.check_and_update_remote_file_sizes",
        name=schedule_name,
        schedule_type=Schedule.CRON,
        cron=settings.FILE_SIZE_CHECK_INTERVAL_CRON,
    )
    logger.info(f"Scheduled file size check with cron expression `{settings.FILE_SIZE_CHECK_INTERVAL_CRON}`")

    return
