import io

from PIL import Image
from django.urls import reverse
from django_webtest import WebTest

from vitrina.projects.factories import ProjectFactory
from vitrina.projects.models import Project


def generate_photo_file() -> io.BytesIO:
    file = io.BytesIO()
    image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))
    image.save(file, 'png')
    file.name = 'test.png'
    file.seek(0)
    return file


class ProjectCreateTest(WebTest):
    csrf_checks = False

    def setUp(self):
        self.image = generate_photo_file()

    def test_project_create(self):
        resp = self.client.post(reverse("project-create"), {
            'title': "Project",
            'description': "Description",
            'url': "example.com",
            'image': self.image
        })
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('project-detail', args=[Project.objects.first().pk]))


class ProjectUpdateTest(WebTest):
    csrf_checks = False

    def setUp(self):
        self.request = ProjectFactory()

    def test_project_update(self):
        resp = self.app.post(reverse("project-update", args=[self.request.pk]), {
            'title': "Updated title",
            'description': "Updated description"
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('project-detail', args=[self.request.pk]))
        self.assertEqual(Project.objects.first().title, "Updated title")
        self.assertEqual(Project.objects.first().description, "Updated description")
