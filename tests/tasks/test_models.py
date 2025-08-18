from datetime import datetime

import pytz
from django.conf import settings
from freezegun import freeze_time

from vitrina.tasks.factories import TaskFactory

timezone = pytz.timezone(settings.TIME_ZONE)


class TestTask:
    def test_update_due_date_when_using_update_fields_without_due_date(self) -> None:
        with freeze_time(datetime(2023, 5, 5, 12, tzinfo=timezone)):
            task = TaskFactory()

        with freeze_time(datetime(2024, 5, 5, 12, tzinfo=timezone)):
            task.save(update_fields=["title"])

        task.refresh_from_db()
        assert task.due_date == datetime(2024, 5, 10, 12, tzinfo=timezone)
