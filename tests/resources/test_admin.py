import pytest
from django.contrib.admin.sites import AdminSite
from django.utils.html import escape

from vitrina.resources.admin import GeoportalFormatAdmin
from vitrina.resources.factories import GeoportalFormatFactory, GeoportalFormatValueFactory
from vitrina.resources.models import GeoportalFormat


@pytest.mark.django_db
def test_values_display_escapes_value():
    xss_payload = "<script>alert('xss')</script>"

    fmt = GeoportalFormatFactory()
    GeoportalFormatValueFactory(geoportal_format=fmt, value=xss_payload)

    result = GeoportalFormatAdmin(GeoportalFormat, AdminSite()).values_display(fmt)

    assert xss_payload not in str(result)
    assert escape(xss_payload) in str(result)
