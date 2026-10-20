from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.utils import timezone
from django.urls import reverse
from django_webtest import DjangoTestApp
from reversion.models import Version

from vitrina.api.models import ApiKey
from vitrina.comments.models import Comment

from vitrina.datasets.factories import DatasetFactory
from vitrina.messages.factories import SubscriptionFactory
from vitrina.messages.models import Subscription
from vitrina.orgs.factories import OrganizationFactory
from vitrina.projects.factories import ProjectFactory, ProjectManagerFactory, UseCaseClientFactory
from vitrina.projects.models import Project
from vitrina.smart_contracts.factories import AgreementFactory
from vitrina.users.factories import UserFactory

pytestmark = pytest.mark.django_db


ALLOWED_USERS = [
    pytest.param(ProjectManagerFactory, id="staff-in-group"),
    pytest.param(lambda: UserFactory(is_superuser=True), id="superuser"),
]


@pytest.fixture
def https_app(app: DjangoTestApp) -> DjangoTestApp:
    app.extra_environ["wsgi.url_scheme"] = "https"
    return app


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


def test_manager_approves_project(https_app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED, is_public=False)
    https_app.set_user(ProjectManagerFactory())

    form = https_app.get(project.get_absolute_url()).forms["project-review-form"]
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


def test_manager_deletes_project(app: DjangoTestApp):
    project = ProjectFactory()
    app.set_user(ProjectManagerFactory())

    resp = app.get(project.get_absolute_url()).click(href=reverse("project-delete", args=[project.pk]))
    resp = resp.forms["delete-form"].submit()

    project.refresh_from_db()
    assert project.deleted is True
    assert project.deleted_on is not None
    assert Version.objects.get_for_object(project).count() == 1
    assert resp.location == reverse("project-list")


@pytest.mark.parametrize("make_user", DENIED_USERS)
def test_non_manager_cannot_delete_project(app: DjangoTestApp, make_user):
    project = ProjectFactory()
    app.set_user(make_user())

    resp = app.get(project.get_absolute_url())
    assert reverse("project-delete", args=[project.pk]) not in resp.text
    resp = app.post(reverse("project-delete", args=[project.pk]), expect_errors=True)

    project.refresh_from_db()
    assert resp.status_code == 403
    assert not project.deleted


@pytest.mark.parametrize("make_user", [ProjectManagerFactory, None])
def test_deleted_project_is_hidden(app: DjangoTestApp, make_user):
    dataset = DatasetFactory()
    project = ProjectFactory(deleted=True, datasets=[dataset])
    visible = ProjectFactory(datasets=[dataset])
    if make_user:
        app.set_user(make_user())

    assert app.get(project.get_absolute_url(), expect_errors=True).status_code == 404
    assert app.get(reverse("project-update", args=[project.pk]), expect_errors=True).status_code in (302, 404)
    assert list(app.get(reverse("project-list")).context["object_list"]) == [visible]
    assert list(app.get(reverse("dataset-projects", args=[dataset.pk])).context["object_list"]) == [visible]


def test_admin_restores_deleted_project(app: DjangoTestApp):
    project = ProjectFactory(deleted=True, deleted_on=timezone.now())
    app.set_user(ProjectManagerFactory())

    resp = app.get(reverse("admin:vitrina_projects_project_changelist") + "?deleted__exact=1")
    form = resp.forms["changelist-form"]
    form["action"] = "restore_projects"
    form.get("_selected_action", index=0).checked = True
    form.submit()

    project.refresh_from_db()
    assert not project.deleted
    assert project.deleted_on is None


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


@pytest.mark.parametrize(
    "add_access",
    [
        pytest.param(lambda project: AgreementFactory(project=project), id="agreement"),
        pytest.param(lambda project: ApiKey.objects.create(project=project), id="api-key"),
        pytest.param(lambda project: UseCaseClientFactory(use_case=project), id="client"),
    ],
)
def test_project_with_data_access_cannot_be_deleted(https_app: DjangoTestApp, add_access):
    project = ProjectFactory()
    add_access(project)
    https_app.set_user(ProjectManagerFactory())

    resp = https_app.get(reverse("project-delete", args=[project.pk]))
    assert resp.location == project.get_absolute_url()
    resp = https_app.post(reverse("project-delete", args=[project.pk])).follow()

    project.refresh_from_db()
    assert not project.deleted
    assert "Negalima ištrinti panaudojimo atvejo" in resp.text


def test_reviewer_is_subscribed_to_replies(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    reviewer = ProjectManagerFactory()
    app.set_user(reviewer)

    form = app.get(project.get_absolute_url()).forms["project-review-form"]
    form.submit("status", value=Project.APPROVED)

    comment = project.comments.get()
    assert Subscription.objects.filter(user=reviewer, object_id=comment.pk, sub_type=Subscription.COMMENT).exists()


def test_project_update_saves_once(app: DjangoTestApp):
    project = ProjectFactory(user=UserFactory())
    app.set_user(ProjectManagerFactory())
    form = app.get(reverse("project-update", args=[project.pk])).forms["project-form"]
    form["description"] = "Updated description"

    with patch("vitrina.search.signals._reindex_datasets") as reindex:
        form.submit()

    assert reindex.call_count == 1
