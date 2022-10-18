import io

import pytest
from PIL import Image
from django.urls import reverse
from django_webtest import DjangoTestApp
from webtest import Upload

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

    assert Project.objects.filter(title='Project').exists()
    assert resp.status_code == 302
    assert resp.url == Project.objects.filter(title='Project').first().get_absolute_url()


@pytest.mark.django_db
def test_project_update(app: DjangoTestApp):
    user = UserFactory()
    request = ProjectFactory(user=user)

    app.set_user(user)

    form = app.get(reverse("project-update", args=[request.pk])).forms['project-form']
    form['title'] = "Updated title"
    form['description'] = "Updated description"
    resp = form.submit()

    request.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == request.get_absolute_url()
    assert request.title == "Updated title"
    assert request.description == "Updated description"
