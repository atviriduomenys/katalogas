import pytest
from django.urls import reverse
from django.utils.html import escape

from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory


@pytest.mark.django_db
class TestUserAdminFlashMessageXSS:
    def test_delete_view_escapes_org_name(self, app, admin_user):
        xss_payload = "<script>alert('xss')</script>"

        org = OrganizationFactory(title=xss_payload)
        user = UserFactory()
        RepresentativeFactory(
            content_object=org,
            user=user,
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        url = reverse("admin:vitrina_users_user_delete", args=[user.pk])
        response = app.get(url, user=admin_user)

        assert xss_payload not in response.text
        assert escape(xss_payload) in response.text
