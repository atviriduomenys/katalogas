import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory, ProjectManagerFactory
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db


ALLOWED_USERS = [
    pytest.param(ProjectManagerFactory, id="staff-in-group"),
    pytest.param(lambda: UserFactory(is_superuser=True), id="superuser"),
]

DENIED_USERS = [
    pytest.param(lambda: UserFactory(is_staff=True), id="staff-outside-group"),
    pytest.param(lambda: ProjectManagerFactory(is_staff=False), id="non-staff-in-group"),
    pytest.param(UserFactory, id="other-user"),
]


@pytest.mark.parametrize("make_user", ALLOWED_USERS)
@pytest.mark.parametrize("with_organization", [False, True])
def test_manager_can_update_any_project(app: DjangoTestApp, make_user, with_organization: bool):
    organization = OrganizationFactory() if with_organization else None
    project = ProjectFactory(user=UserFactory(), organization=organization)
    app.set_user(make_user())

    form = app.get(reverse("project-update", args=[project.pk])).forms["project-form"]
    form["title"] = "Updated title"
    form["description"] = "Updated description"
    form.submit()

    project.refresh_from_db()
    assert project.title == "Updated title"


@pytest.mark.parametrize("make_user", DENIED_USERS)
def test_non_manager_cannot_update_project(app: DjangoTestApp, make_user):
    project = ProjectFactory(user=UserFactory())
    app.set_user(make_user())

    resp = app.get(reverse("project-update", args=[project.pk]), expect_errors=True)

    assert resp.status_code == 403
