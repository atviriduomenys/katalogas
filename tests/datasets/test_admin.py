import pytest
from django.contrib.admin.sites import AdminSite
from django.utils.html import escape

from vitrina.datasets.admin import DatasetReportAdmin
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Representative

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
