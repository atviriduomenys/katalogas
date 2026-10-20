import pytest
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.urls import reverse
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina.comments.models import Comment

from vitrina.messages.factories import SubscriptionFactory
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory, ProjectManagerFactory
from vitrina.projects.models import Project
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


def test_manager_approves_project(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED, is_public=False)
    app.set_user(ProjectManagerFactory())

    form = app.get(project.get_absolute_url()).forms["project-review-form"]
    form["body"] = "Reviewed"
    resp = form.submit("status", value=Project.APPROVED).follow()

    project.refresh_from_db()
    assert project.status == Project.APPROVED
    assert project.is_public is False
    comment = project.comments.get()
    assert (comment.type, comment.status, comment.body) == (Comment.STATUS, Comment.APPROVED, "Reviewed")
    assert not Comment.objects.filter(content_type__model="request").exists()
    assert Version.objects.get_for_object(project).count() == 1
    assert "Panaudojimo atvejis patvirtintas" in resp.text


def test_manager_approves_project_without_comment(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    app.set_user(ProjectManagerFactory())

    form = app.get(project.get_absolute_url()).forms["project-review-form"]
    form.submit("status", value=Project.APPROVED)

    project.refresh_from_db()
    assert project.status == Project.APPROVED


def test_reject_requires_comment(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    app.set_user(ProjectManagerFactory())

    form = app.get(project.get_absolute_url()).forms["project-review-form"]
    form.submit("status", value=Project.REJECTED)

    project.refresh_from_db()
    assert project.status == Project.CREATED
    assert not project.comments.exists()


def test_manager_rejects_project(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    app.set_user(ProjectManagerFactory())

    form = app.get(project.get_absolute_url()).forms["project-review-form"]
    form["body"] = "Link does not work"
    form.submit("status", value=Project.REJECTED)

    project.refresh_from_db()
    assert project.status == Project.REJECTED
    assert project.comments.get().status == Comment.REJECTED


def test_review_with_same_status_is_ignored(app: DjangoTestApp):
    project = ProjectFactory(status=Project.APPROVED)
    app.set_user(ProjectManagerFactory())

    form = app.get(project.get_absolute_url()).forms["project-review-form"]
    form.submit("status", value=Project.APPROVED)

    assert not project.comments.exists()
    assert Version.objects.get_for_object(project).count() == 0


@pytest.mark.parametrize("make_user", DENIED_USERS)
def test_non_manager_cannot_review_project(app: DjangoTestApp, make_user):
    project = ProjectFactory(status=Project.CREATED)
    app.set_user(make_user())

    resp = app.get(project.get_absolute_url(), expect_errors=True)
    assert "project-review-form" not in resp.forms
    resp = app.post(reverse("project-review", args=[project.pk]), {"status": Project.APPROVED}, expect_errors=True)

    project.refresh_from_db()
    assert resp.status_code == 403
    assert project.status == Project.CREATED


def test_comment_form_has_no_status(app: DjangoTestApp):
    project = ProjectFactory()
    app.set_user(ProjectManagerFactory())

    form = app.get(project.get_absolute_url()).forms["comment-form"]

    assert "status" not in form.fields


@pytest.mark.parametrize("is_public, label", [(True, "Taip"), (False, "Ne")])
def test_detail_shows_visibility(app: DjangoTestApp, is_public: bool, label: str):
    project = ProjectFactory(is_public=is_public)
    app.set_user(ProjectManagerFactory())

    resp = app.get(project.get_absolute_url())

    assert resp.html.find(id="project-visibility").get_text(strip=True) == label


@pytest.mark.parametrize(
    "status, body, expected",
    [
        (Project.APPROVED, "", "Būsena pakeista: Patvirtintas"),
        (Project.REJECTED, "Nuoroda neveikia", "Būsena pakeista: Atmestas"),
    ],
)
def test_author_sees_review_feedback(app: DjangoTestApp, status: str, body: str, expected: str):
    author = UserFactory()
    project = ProjectFactory(user=author, status=Project.CREATED, is_public=False)
    SubscriptionFactory(
        user=author,
        content_type=ContentType.objects.get_for_model(Project),
        object_id=project.pk,
        sub_type=Subscription.PROJECT,
        project_comments_sub=True,
    )
    app.set_user(ProjectManagerFactory())
    form = app.get(project.get_absolute_url()).forms["project-review-form"]
    form["body"] = body
    form.submit("status", value=status)

    app.set_user(author)
    comments = app.get(project.get_absolute_url()).html.find(id="comments").find_parent().get_text(" ", strip=True)

    assert expected in comments
    assert body in comments
    assert [message.to for message in mail.outbox] == [[author.email]]
    assert expected in mail.outbox[0].body
    assert body in mail.outbox[0].body
