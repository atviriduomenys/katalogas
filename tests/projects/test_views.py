import io

import pytest
from PIL import Image
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp
from reversion.models import Version
from webtest import Upload

from vitrina.comments.models import Comment
from vitrina.projects.factories import ProjectFactory
from vitrina.projects.models import Project
from vitrina.users.factories import UserFactory


def generate_photo_file() -> bytes:
    file = io.BytesIO()
    image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
    image.save(file, 'png')
    file.name = 'example.png'
    return file.getvalue()


@pytest.mark.django_db
def test_project_create(app: DjangoTestApp):
    user = UserFactory()
    app.set_user(user)

    form = app.get(reverse("project-create")).forms['project-form']
    form['title'] = "Project"
    form['description'] = "Description"
    form['url'] = "example.com"
    form['image'] = Upload('example.png', generate_photo_file(), 'image')
    resp = form.submit()

    added_project = Project.objects.filter(title='Project')
    assert added_project.exists()
    assert resp.status_code == 302
    assert resp.url == added_project.first().get_absolute_url()
    assert Version.objects.get_for_object(added_project.first()).count() == 1
    assert Version.objects.get_for_object(added_project.first()).first().revision.comment == Project.CREATED


@pytest.mark.django_db
def test_project_update(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(user=user)

    app.set_user(user)

    form = app.get(reverse("project-update", args=[project.pk])).forms['project-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit()

    project.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == project.get_absolute_url()
    assert project.title == "Updated title"
    assert project.description == "Updated description"
    assert Version.objects.get_for_object(project).count() == 1
    assert Version.objects.get_for_object(project).first().revision.comment == Project.EDITED


@pytest.mark.django_db
def test_project_history_view_without_permission(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory()
    app.set_user(user)
    resp = app.get(reverse('project-history', args=[project.pk]), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_project_history_view_with_permission(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory()
    app.set_user(user)

    form = app.get(reverse("project-update", args=[project.pk])).forms['project-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit().follow()
    resp = resp.click(linkid="history-tab")
    assert resp.context['detail_url_name'] == 'project-detail'
    assert resp.context['history_url_name'] == 'project-history'
    assert len(resp.context['history']) == 1
    assert resp.context['history'][0]['action'] == "Redaguota"
    assert resp.context['history'][0]['user'] == user


@pytest.mark.django_db
def test_request_comment_with_status(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory()
    app.set_user(user)

    form = app.get(project.get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['status'] = Comment.APPROVED
    form['body'] = "Approving this project"
    resp = form.submit().follow()

    comment = project.comments.get()
    assert list(resp.context['comments']) == [(comment, [])]
    assert comment.type == Comment.STATUS
    assert comment.status == Comment.APPROVED

    version = Version.objects.get_for_object(project).get()
    assert version.revision.comment == Project.STATUS_CHANGED


@pytest.mark.django_db
def test_request_comment_with_status_rejected(app: DjangoTestApp):
    project = ProjectFactory()
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(project.get_absolute_url()).forms['comment-form']
    form['is_public'] = True
    form['status'] = Comment.REJECTED
    form['body'] = ""
    resp = form.submit().follow()

    comment = project.comments.get()
    assert list(resp.context['comments']) == [(comment, [])]
    assert comment.type == Comment.STATUS
    assert comment.status == Comment.REJECTED

    version = Version.objects.get_for_object(project).get()
    assert version.revision.comment == Project.STATUS_CHANGED


@pytest.mark.django_db
def test_request_comment_with_same_status(app: DjangoTestApp):
    project = ProjectFactory(status=Project.APPROVED)
    user = UserFactory(is_staff=True)
    app.set_user(user)

    form = app.get(project.get_absolute_url()).forms['comment-form']
    form['status'] = Comment.APPROVED
    form.submit().follow()

    assert project.comments.count() == 0
    assert Version.objects.get_for_object(project).count() == 0
