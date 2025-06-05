import unittest
from unittest.mock import patch, MagicMock

from vitrina.resources.schedule import setup_file_size_check_schedule


class TestFileSchedule(unittest.TestCase):
    @patch('vitrina.resources.schedule.Schedule')
    @patch('vitrina.resources.schedule.schedule')
    @patch('vitrina.resources.schedule.settings')
    @patch('vitrina.resources.schedule.logger')
    def test_setup_file_size_check_schedule(self, mock_logger, mock_settings, mock_schedule, mock_Schedule):
        mock_settings.FILE_SIZE_CHECK_INTERVAL_CRON = "0 2 * * *"
        mock_filter = MagicMock()
        mock_Schedule.objects.filter.return_value = mock_filter

        setup_file_size_check_schedule()

        mock_Schedule.objects.filter.assert_called_once_with(name="check_file_sizes")
        mock_filter.delete.assert_called_once()

        mock_schedule.assert_called_once_with(
            "vitrina.resources.tasks.check_and_update_file_sizes",
            name="check_file_sizes",
            schedule_type=mock_Schedule.CRON,
            cron="0 2 * * *"
        )

        mock_logger.info.assert_called_once_with(
            "Scheduled file size check with cron expression `0 2 * * *`"
        )

    @patch('vitrina.resources.schedule.Schedule')
    @patch('vitrina.resources.schedule.schedule')
    @patch('vitrina.resources.schedule.settings')
    def test_returns_none(self, mock_settings, mock_schedule, mock_Schedule):
        mock_settings.FILE_SIZE_CHECK_INTERVAL_CRON = "0 2 * * *"

        result = setup_file_size_check_schedule()

        self.assertIsNone(result)