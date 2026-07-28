import pytest
from django.utils.html import escape

from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory
from vitrina.users.forms import UserChangeAdminForm


@pytest.mark.django_db
class TestUserAdminFormXSS:
    def test_organizations_and_roles_escapes_org_name(self):
        xss_payload = "<script>alert('xss')</script>"

        org = OrganizationFactory(title=xss_payload)
        user = UserFactory()
        RepresentativeFactory(
            content_object=org,
            user=user,
            role=Representative.OPEN_DATA_COORDINATOR,
        )

        form = UserChangeAdminForm(instance=user)
        result = form.initial.get("organizations_and_roles", "")

        assert xss_payload not in str(result)
        assert escape(xss_payload) in str(result)
