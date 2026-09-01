import pytest
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db

# Every view of the wizard takes its access rules from `WizardAccessMixin`.
WIZARD_URL_NAMES = [
    "organization-wizard",
    "organization-wizard-tree",
    "organization-wizard-nodes",
    "organization-wizard-create",
]


def _representative(org, role: str) -> Representative:
    return RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(org),
        object_id=org.pk,
        role=role,
    )


class TestOrganizationWizardView:
    @pytest.mark.parametrize("url_name", WIZARD_URL_NAMES)
    def test_unauthenticated_redirects_to_login(self, app: DjangoTestApp, url_name: str):
        org = OrganizationFactory()
        url = reverse(url_name, kwargs={"pk": org.pk})

        response = app.get(url)

        assert response.status_code == 302
        assert settings.LOGIN_URL in response.location
        assert url in response.location

    @pytest.mark.parametrize("url_name", WIZARD_URL_NAMES)
    def test_unrelated_user_is_redirected_to_organization(self, app: DjangoTestApp, url_name: str):
        org = OrganizationFactory()
        app.set_user(UserFactory())

        response = app.get(reverse(url_name, kwargs={"pk": org.pk}))

        assert response.status_code == 302
        assert response.location == reverse("organization-detail", kwargs={"pk": org.pk})

    def test_representative_of_another_organization_is_redirected(self, app: DjangoTestApp):
        org = OrganizationFactory()
        other_org = OrganizationFactory()
        app.set_user(_representative(other_org, Representative.RESOURCE_MANAGER).user)

        response = app.get(reverse("organization-wizard", kwargs={"pk": org.pk}))

        assert response.status_code == 302
        assert response.location == reverse("organization-detail", kwargs={"pk": org.pk})

    def test_open_data_role_is_redirected(self, app: DjangoTestApp):
        org = OrganizationFactory()
        app.set_user(_representative(org, Representative.OPEN_DATA_COORDINATOR).user)

        response = app.get(reverse("organization-wizard", kwargs={"pk": org.pk}))

        assert response.status_code == 302
        assert response.location == reverse("organization-detail", kwargs={"pk": org.pk})

    def test_deleted_representative_is_redirected(self, app: DjangoTestApp):
        # Only the shell is closed to a soft-deleted representative. `has_perm` ignores the
        # `deleted` flag, so the forms behind the shell still answer such a row. Nothing in the
        # code sets the flag today (the member views delete the row), so this guards the helper,
        # not a live revocation path.
        org = OrganizationFactory()
        rep = _representative(org, Representative.RESOURCE_MANAGER)
        rep.deleted = True
        rep.save()
        app.set_user(rep.user)

        response = app.get(reverse("organization-wizard", kwargs={"pk": org.pk}))

        assert response.status_code == 302
        assert response.location == reverse("organization-detail", kwargs={"pk": org.pk})

    @pytest.mark.parametrize("role", [Representative.RESOURCE_COORDINATOR, Representative.RESOURCE_MANAGER])
    def test_resource_role_gets_200(self, app: DjangoTestApp, role: str):
        org = OrganizationFactory()
        app.set_user(_representative(org, role).user)

        response = app.get(reverse("organization-wizard", kwargs={"pk": org.pk}))

        assert response.status_code == 200

    def test_superuser_gets_200(self, app: DjangoTestApp):
        org = OrganizationFactory()
        app.set_user(UserFactory(is_superuser=True))

        response = app.get(reverse("organization-wizard", kwargs={"pk": org.pk}))

        assert response.status_code == 200


class TestOrganizationDetailWizardButton:
    @pytest.mark.parametrize("role", [Representative.RESOURCE_COORDINATOR, Representative.RESOURCE_MANAGER])
    def test_resource_role_sees_button(self, app: DjangoTestApp, role: str):
        org = OrganizationFactory()
        app.set_user(_representative(org, role).user)

        response = app.get(reverse("organization-detail", kwargs={"pk": org.pk}))

        assert response.html.find(id="open_organization_wizard") is not None

    def test_superuser_sees_button(self, app: DjangoTestApp):
        org = OrganizationFactory()
        app.set_user(UserFactory(is_superuser=True))

        response = app.get(reverse("organization-detail", kwargs={"pk": org.pk}))

        assert response.html.find(id="open_organization_wizard") is not None

    def test_coordinator_still_sees_organization_edit_button(self, app: DjangoTestApp):
        org = OrganizationFactory()
        app.set_user(_representative(org, Representative.RESOURCE_COORDINATOR).user)

        response = app.get(reverse("organization-detail", kwargs={"pk": org.pk}))

        assert response.html.find(id="change_organization") is not None

    def test_unrelated_user_sees_no_button(self, app: DjangoTestApp):
        org = OrganizationFactory()
        app.set_user(UserFactory())

        response = app.get(reverse("organization-detail", kwargs={"pk": org.pk}))

        assert response.html.find(id="open_organization_wizard") is None
