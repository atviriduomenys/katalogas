from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin.sites import AdminSite
from django.utils.html import escape

from vitrina.datasets.admin import DatasetReportAdmin
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.resources.factories import DatasetDistributionFactory

XSS_PAYLOAD = "<script>alert('xss')</script>"


@pytest.mark.django_db
class TestDatasetReportAdminXSS:
    def setup_method(self):
        self.admin = DatasetReportAdmin(Dataset, AdminSite())

    def test_coordinators_display_escapes_email(self):
        dataset = DatasetFactory()
        RepresentativeFactory(
            content_object=dataset,
            role=Representative.OPEN_DATA_COORDINATOR,
            email=XSS_PAYLOAD,
        )

        result = self.admin.coordinators_display(dataset)

        assert XSS_PAYLOAD not in str(result)
        assert escape(XSS_PAYLOAD) in str(result)

    def test_managers_display_escapes_email(self):
        dataset = DatasetFactory()
        RepresentativeFactory(
            content_object=dataset,
            role=Representative.OPEN_DATA_MANAGER,
            email=XSS_PAYLOAD,
        )

        result = self.admin.managers_display(dataset)

        assert XSS_PAYLOAD not in str(result)
        assert escape(XSS_PAYLOAD) in str(result)


def _spinta_response(url: str, *args, **kwargs) -> MagicMock:
    response = MagicMock()
    if url.endswith("/:ns/?"):
        response.content = b'{"_data": [{"name": "datasets/gov/ns/Model"}]}'
    else:
        response.content = b'{"_data": [{"_created": "2026-05-14T06:12:15"}]}'
    return response


@pytest.mark.django_db
@pytest.mark.parametrize(
    "download_url",
    [
        "https://get.data.gov.lt/datasets/gov/ns/Model",
        "https://get.data.gov.lt/datasets/gov/ns/:ns",
    ],
)
def test_spinta_modified_display_requests_normalized_urls(download_url):
    dataset = DatasetFactory()
    DatasetDistributionFactory(dataset=dataset, uapi_format=True, download_url=download_url)
    report_admin = DatasetReportAdmin(Dataset, AdminSite())

    with patch("vitrina.structure.services.requests.get", side_effect=_spinta_response) as mock_get:
        result = report_admin.spinta_modified_display(dataset)

    requested_urls = [call.args[0] for call in mock_get.call_args_list]
    assert requested_urls[-1].endswith("/datasets/gov/ns/Model/:changes/-1/?")
    assert all("//" not in url.split("://", 1)[1] for url in requested_urls)
    assert result == "2026-05-14 06:12"
