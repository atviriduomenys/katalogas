import pytest
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Representative
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db

# Every wizard view takes its access rules from `WizardAccessMixin`.
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


def _role_user(role: str):
    return lambda org: _representative(org, role).user


def _unrelated_user(org):
    return UserFactory()


def _superuser(org):
    return UserFactory(is_superuser=True)


def _other_organization_manager(org):
    return _representative(OrganizationFactory(), Representative.RESOURCE_MANAGER).user


def _deleted_resource_manager(org):
    rep = _representative(org, Representative.RESOURCE_MANAGER)
    rep.deleted = True
    rep.save()
    return rep.user


DENIED_USERS = [
    pytest.param(_unrelated_user, id="unrelated"),
    pytest.param(_other_organization_manager, id="other-organization-manager"),
    pytest.param(_role_user(Representative.OPEN_DATA_COORDINATOR), id="open-data-coordinator"),
    # `has_perm` ignores `deleted`, so only the shell closes for a soft-deleted representative.
    pytest.param(_deleted_resource_manager, id="deleted-resource-manager"),
]

ALLOWED_USERS = [
    pytest.param(_role_user(Representative.RESOURCE_COORDINATOR), id="resource-coordinator"),
    pytest.param(_role_user(Representative.RESOURCE_MANAGER), id="resource-manager"),
    pytest.param(_superuser, id="superuser"),
]


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
    @pytest.mark.parametrize("make_user", DENIED_USERS)
    def test_denied_user_is_redirected_to_organization(self, app: DjangoTestApp, make_user, url_name: str):
        org = OrganizationFactory()
        app.set_user(make_user(org))

        response = app.get(reverse(url_name, kwargs={"pk": org.pk}))

        assert response.status_code == 302
        assert response.location == reverse("organization-detail", kwargs={"pk": org.pk})

    @pytest.mark.parametrize("make_user", ALLOWED_USERS)
    def test_allowed_user_gets_200(self, app: DjangoTestApp, make_user):
        org = OrganizationFactory()
        app.set_user(make_user(org))

        response = app.get(reverse("organization-wizard", kwargs={"pk": org.pk}))

        assert response.status_code == 200

    def test_pane_asks_for_the_organization_form(self, app: DjangoTestApp):
        org = OrganizationFactory()
        app.set_user(_representative(org, Representative.RESOURCE_COORDINATOR).user)

        response = app.get(reverse("organization-wizard", kwargs={"pk": org.pk}))

        pane = response.html.find(id="wizard-main-pane")
        assert pane["hx-get"] == reverse("organization-change", kwargs={"pk": org.pk})
        assert pane["x-show"] == "mode !== 'create'"
        assert response.html.find(id="wizard-org-notice") is None

    def test_pane_explains_the_missing_organization_form(self, app: DjangoTestApp):
        # Asking for a form the resource manager may not open answers a redirect that HTMX would
        # swap into the pane as a whole page, so a notice keyed to the organization node takes
        # its place — outside the pane, which an HTMX swap empties.
        org = OrganizationFactory()
        app.set_user(_representative(org, Representative.RESOURCE_MANAGER).user)

        response = app.get(reverse("organization-wizard", kwargs={"pk": org.pk}))

        pane = response.html.find(id="wizard-main-pane")
        notice = response.html.find(id="wizard-org-notice")
        assert pane.get("hx-get") is None
        assert f"!(selected && selected.key === 'org:{org.pk}')" in pane["x-show"]
        assert notice is not None
        assert notice not in pane.find_all("div")
        assert notice["x-show"] == f"mode === 'detail' && selected && selected.key === 'org:{org.pk}'"
        # A `{# #}` comment that spans lines renders as plain text.
        assert "{#" not in response.text

    def test_resource_manager_can_return_to_the_organization_node(self, app: DjangoTestApp):
        # Without a `select(...)` call the row only toggles the subtree, so a manager who opened a
        # child form could never get the pane back to the organization state.
        org = OrganizationFactory()
        app.set_user(_representative(org, Representative.RESOURCE_MANAGER).user)

        response = app.get(reverse("organization-wizard", kwargs={"pk": org.pk}))

        root_row = response.html.find("li", class_="wizard-tree-root").find("div", class_="wizard-tree-row")
        assert f"select('org:{org.pk}')" in root_row["@click.stop"]
        assert root_row.get("hx-get") is None


class TestOrganizationDetailWizardButton:
    @pytest.mark.parametrize(
        ("make_user", "sees_wizard", "sees_edit"),
        [
            # The two resource roles reach the organization form from the wizard's root node
            # instead, so this page stops offering it to them.
            pytest.param(_role_user(Representative.RESOURCE_COORDINATOR), True, False, id="resource-coordinator"),
            pytest.param(_role_user(Representative.RESOURCE_MANAGER), True, False, id="resource-manager"),
            pytest.param(_superuser, True, True, id="superuser"),
            # Nothing changes for the open data roles: only their coordinator may update the
            # organization, and none of them reaches the wizard.
            pytest.param(_role_user(Representative.OPEN_DATA_COORDINATOR), False, True, id="open-data-coordinator"),
            pytest.param(_role_user(Representative.OPEN_DATA_MANAGER), False, False, id="open-data-manager"),
            pytest.param(_role_user(Representative.OPEN_DATA_PUBLISHER), False, False, id="open-data-publisher"),
            pytest.param(_unrelated_user, False, False, id="unrelated"),
        ],
    )
    def test_buttons_offered_to_each_role(self, app: DjangoTestApp, make_user, sees_wizard: bool, sees_edit: bool):
        org = OrganizationFactory()
        app.set_user(make_user(org))

        response = app.get(reverse("organization-detail", kwargs={"pk": org.pk}))

        assert (response.html.find(id="open_organization_wizard") is not None) is sees_wizard
        assert (response.html.find(id="change_organization") is not None) is sees_edit
