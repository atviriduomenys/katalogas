import pytest
from django.contrib.admin.sites import AdminSite
from django.utils.html import escape

from vitrina.statistics.admin import StatRouteAdmin
from vitrina.statistics.models import StatRoute


@pytest.mark.django_db
class TestStatRouteAdminXSS:
    def test_formatted_url_escapes_url(self):
        xss_payload = "<script>alert('xss')</script>"

        stat_route = StatRoute.objects.create(url=xss_payload)

        result = StatRouteAdmin(StatRoute, AdminSite()).formatted_url(stat_route)

        assert xss_payload not in str(result)
        assert escape(xss_payload) in str(result)
