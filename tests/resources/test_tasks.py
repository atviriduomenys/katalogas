import unittest
from unittest.mock import patch, MagicMock, Mock

import requests

from vitrina.resources.tasks import (
    FileInfo,
    check_and_update_remote_file_sizes,
    update_remote_file_size,
    get_remote_file_info,
)


class TestFileInfo(unittest.TestCase):
    def test_file_info_dataclass(self):
        info = FileInfo(size=1024, last_modified="2025-01-01 10:00")
        self.assertEqual(info.size, 1024)
        self.assertEqual(info.last_modified, "2025-01-01 10:00")

        info_default = FileInfo()
        self.assertIsNone(info_default.size)
        self.assertIsNone(info_default.last_modified)


class TestCheckAndUpdateFileSizes(unittest.TestCase):
    @patch('vitrina.resources.tasks.DatasetDistribution')
    def test_no_distributions(self, mock_dist_model):
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 0
        mock_dist_model.objects.filter.return_value = mock_queryset

        results = check_and_update_remote_file_sizes()

        self.assertEqual(results, {"total": 0, "updated": 0, "unchanged": 0, "errors": 0})

    @patch('vitrina.resources.tasks.update_remote_file_size')
    @patch('vitrina.resources.tasks.DatasetDistribution')
    def test_remote_file_distribution(self, mock_dist_model, mock_update_remote):
        dist = MagicMock()
        dist.pk = 1
        dist.get_download_url.return_value = "https://example.com/file.csv"

        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.__iter__ = Mock(return_value=iter([dist]))
        mock_dist_model.objects.filter.return_value = mock_queryset

        results = check_and_update_remote_file_sizes()

        self.assertEqual(results["total"], 1)
        mock_update_remote.assert_called_once_with(dist, "https://example.com/file.csv", results)

    @patch('vitrina.resources.tasks.logger')
    @patch('vitrina.resources.tasks.DatasetDistribution')
    def test_exception_handling(self, mock_dist_model, mock_logger):
        dist = MagicMock()
        dist.pk = 1

        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 1
        mock_queryset.__iter__ = Mock(return_value=iter([dist]))
        mock_dist_model.objects.filter.return_value = mock_queryset

        results = check_and_update_remote_file_sizes()

        self.assertEqual(results["errors"], 1)
        mock_logger.error.assert_called_once()


class TestUpdateRemoteFileSize(unittest.TestCase):
    @patch('vitrina.resources.tasks.get_remote_file_info')
    def test_file_info_no_size(self, mock_get_info):
        dist = MagicMock()
        mock_get_info.return_value = FileInfo(size=None)
        results = {"updated": 0, "unchanged": 0, "errors": 0}

        update_remote_file_size(dist, "https://example.com/file.csv", results)

        self.assertEqual(results["errors"], 1)
        dist.save.assert_not_called()

    @patch('vitrina.resources.tasks.get_remote_file_info')
    def test_size_unchanged(self, mock_get_info):
        dist = MagicMock()
        dist.size = 1024
        mock_get_info.return_value = FileInfo(size=1024)
        results = {"updated": 0, "unchanged": 0, "errors": 0}

        update_remote_file_size(dist, "https://example.com/file.csv", results)

        self.assertEqual(results["unchanged"], 1)
        dist.save.assert_not_called()

    @patch('vitrina.resources.tasks.logger')
    @patch('vitrina.resources.tasks.get_remote_file_info')
    def test_size_updated_without_last_modified(self, mock_get_info, mock_logger):
        dist = MagicMock()
        dist.pk = 1
        dist.size = 1024
        mock_get_info.return_value = FileInfo(size=2048, last_modified=None)
        results = {"updated": 0, "unchanged": 0, "errors": 0}

        update_remote_file_size(dist, "https://example.com/file.csv", results)

        self.assertEqual(results["updated"], 1)
        self.assertEqual(dist.size, 2048)
        dist.save.assert_called_once_with(update_fields=["size"])
        mock_logger.info.assert_called_once()

    @patch('vitrina.resources.tasks.logger')
    @patch('vitrina.resources.tasks.get_remote_file_info')
    def test_size_and_last_modified_updated(self, mock_get_info, mock_logger):
        dist = MagicMock()
        dist.pk = 1
        dist.size = 1024
        type(dist).last_modified = Mock()
        mock_get_info.return_value = FileInfo(
            size=2048,
            last_modified="2025-01-01 10:00"
        )
        results = {"updated": 0, "unchanged": 0, "errors": 0}

        update_remote_file_size(dist, "https://example.com/file.csv", results)

        self.assertEqual(results["updated"], 1)
        self.assertEqual(dist.size, 2048)
        self.assertEqual(dist.last_modified, "2025-01-01 10:00")
        dist.save.assert_called_once_with(update_fields=["size", "last_modified"])


class TestGetRemoteFileInfo(unittest.TestCase):
    @patch('requests.head')
    def test_head_request_with_content_length(self, mock_head):
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Length": "1024",
            "Last-Modified": "2025-01-01 10:00"
        }
        mock_head.return_value = mock_response

        file_info = get_remote_file_info("https://example.com/file.csv")

        self.assertEqual(file_info.size, 1024)
        self.assertEqual(file_info.last_modified, "2025-01-01 10:00")
        mock_head.assert_called_once_with(
            "https://example.com/file.csv",
            allow_redirects=True,
            timeout=5
        )

    @patch('vitrina.resources.tasks.logger')
    @patch('requests.head')
    def test_invalid_content_length(self, mock_head, mock_logger):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": "invalid"}
        mock_head.return_value = mock_response

        with patch('requests.get') as mock_get:
            mock_get_response = MagicMock()
            mock_get_response.iter_content.return_value = [b'x' * 100]
            mock_get_response.__enter__.return_value = mock_get_response
            mock_get.return_value = mock_get_response

            file_info = get_remote_file_info("https://example.com/file.csv")

        self.assertEqual(file_info.size, 100)
        mock_logger.warning.assert_called_once()

    @patch('requests.get')
    @patch('requests.head')
    def test_no_content_length_download_file(self, mock_head, mock_get):
        mock_head_response = MagicMock()
        mock_head_response.headers = {}
        mock_head.return_value = mock_head_response

        mock_get_response = MagicMock()
        mock_get_response.iter_content.return_value = [b'x' * 1000, b'y' * 500]
        mock_get_response.__enter__.return_value = mock_get_response
        mock_get.return_value = mock_get_response

        file_info = get_remote_file_info("https://example.com/file.csv")

        self.assertEqual(file_info.size, 1500)

    @patch('vitrina.resources.tasks.logger')
    @patch('requests.get')
    @patch('requests.head')
    def test_file_exceeds_max_size(self, mock_head, mock_get, mock_logger):
        mock_head_response = MagicMock()
        mock_head_response.headers = {}
        mock_head.return_value = mock_head_response

        mock_get_response = MagicMock()
        mock_get_response.iter_content.return_value = [b'x' * 1000] * 3
        mock_get_response.__enter__.return_value = mock_get_response
        mock_get.return_value = mock_get_response

        file_info = get_remote_file_info("https://example.com/file.csv", max_size=2000)

        self.assertEqual(file_info.size, 3000)
        mock_logger.warning.assert_called_once()

    @patch('vitrina.resources.tasks.logger')
    @patch('requests.head')
    def test_request_exception(self, mock_head, mock_logger):
        mock_head.side_effect = requests.exceptions.RequestException("Connection error")

        file_info = get_remote_file_info("https://example.com/file.csv")

        self.assertIsNone(file_info.size)
        self.assertIsNone(file_info.last_modified)
        mock_logger.error.assert_called_once()

    @patch('vitrina.resources.tasks.logger')
    @patch('requests.head')
    def test_unexpected_exception(self, mock_head, mock_logger):
        mock_head.side_effect = Exception("Unexpected error")

        get_remote_file_info("https://example.com/file.csv")

        mock_logger.error.assert_called_once()
