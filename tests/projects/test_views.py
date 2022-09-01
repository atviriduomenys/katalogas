import io

import pytest
from PIL import Image
from django.urls import reverse
from django.test import Client

from vitrina.projects.factories import ProjectFactory
from vitrina.projects.models import Project


def generate_photo_file():
    file = io.BytesIO()
    image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
    image.save(file, 'png')
    file.name = 'test.png'
    file.seek(0)
    return file


@pytest.mark.django_db
def test_project_create(client: Client):
    image = generate_photo_file()
    resp = client.post(reverse("project-create"), data={
        'title': "Project",
        'description': "Description",
        'url': "example.com",
        'image': image
    })
    assert Project.objects.count() == 1
    assert resp.status_code == 302
    assert resp.url == reverse('project-detail', args=[Project.objects.first().pk])


@pytest.mark.django_db
def test_project_update(client: Client):
    request = ProjectFactory()
    resp = client.post(reverse("project-update", args=[request.pk]), data={'title': "Updated title",
                                                                           'description': "Updated description"})
    assert resp.status_code == 302
    assert resp.url == reverse('project-detail', args=[request.pk])
    assert Project.objects.first().title == "Updated title"
    assert Project.objects.first().description == "Updated description"
