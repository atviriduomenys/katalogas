import io

import pytest
from PIL import Image
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.projects.factories import ProjectFactory
from vitrina.projects.models import Project


def generate_photo_file() -> bytes:
    file = io.BytesIO()
    image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
    image.save(file, 'png')
    file.name = 'example.png'
    return file.getvalue()


@pytest.mark.django_db
def test_project_create(csrf_exempt_django_app: DjangoTestApp):
    resp = csrf_exempt_django_app.post(reverse("project-create"), {
        'title': "Project",
        'description': "Description",
        'url': "example.com",
    }, upload_files=[('image', 'example.png', generate_photo_file())])

    assert Project.objects.count() == 1
    assert resp.status_code == 302
    assert resp.url == reverse('project-detail', args=[Project.objects.first().pk])


@pytest.mark.django_db
def test_project_update(csrf_exempt_django_app: DjangoTestApp):
    request = ProjectFactory()
    resp = csrf_exempt_django_app.post(reverse("project-update", args=[request.pk]), {
        'title': "Updated title",
        'description': "Updated description"
    })
    assert resp.status_code == 302
    assert resp.url == reverse('project-detail', args=[request.pk])
    assert Project.objects.first().title == "Updated title"
    assert Project.objects.first().description == "Updated description"
