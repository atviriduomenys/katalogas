from django.contrib.auth.models import User
from django.urls import reverse

from django_webtest import WebTest
from hitcount.models import HitCount

from vitrina.datasets.factories import DatasetFactory
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory


class DatasetViewCountTest(WebTest):
    csrf_checks = False

    def setUp(self):
        self.dataset = DatasetFactory()
        self.hit_count = HitCount.objects.create(content_object=self.dataset)
        self.user1 = User.objects.create_user(username='user1', password='12345')
        self.user2 = User.objects.create_user(username='user2', password='12345')

    def test_hit_count(self):
        # with one user
        self.app.set_user(self.user1)
        resp = self.app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': self.hit_count.pk}, xhr=True)
        self.assertEqual(resp.content, b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}')
        self.assertEqual(HitCount.objects.get(pk=self.hit_count.pk).hits, 1)

        # with the same user
        resp = self.app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': self.hit_count.pk}, xhr=True)
        self.assertEqual(resp.content,
                         b'{"hit_counted": false, "hit_message": "Not counted: authenticated user has active hit"}')
        self.assertEqual(HitCount.objects.get(pk=self.hit_count.pk).hits, 1)

        # with another user
        self.app.set_user(self.user2)
        resp = self.app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': self.hit_count.pk}, xhr=True)
        self.assertEqual(resp.content, b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}')
        self.assertEqual(HitCount.objects.get(pk=self.hit_count.pk).hits, 2)


class RequestViewCountTest(WebTest):
    csrf_checks = False

    def setUp(self):
        self.request = RequestFactory()
        self.hit_count = HitCount.objects.create(content_object=self.request)
        self.user1 = User.objects.create_user(username='user1', password='12345')
        self.user2 = User.objects.create_user(username='user2', password='12345')

    def test_hit_count(self):
        # with one user
        self.app.set_user(self.user1)
        resp = self.app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': self.hit_count.pk}, xhr=True)
        self.assertEqual(resp.content, b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}')
        self.assertEqual(HitCount.objects.get(pk=self.hit_count.pk).hits, 1)

        # with the same user
        resp = self.app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': self.hit_count.pk}, xhr=True)
        self.assertEqual(resp.content,
                         b'{"hit_counted": false, "hit_message": "Not counted: authenticated user has active hit"}')
        self.assertEqual(HitCount.objects.get(pk=self.hit_count.pk).hits, 1)

        # with another user
        self.app.set_user(self.user2)
        resp = self.app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': self.hit_count.pk}, xhr=True)
        self.assertEqual(resp.content, b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}')
        self.assertEqual(HitCount.objects.get(pk=self.hit_count.pk).hits, 2)


class ProjectViewCountTest(WebTest):
    csrf_checks = False

    def setUp(self):
        self.project = ProjectFactory()
        self.hit_count = HitCount.objects.create(content_object=self.project)
        self.user1 = User.objects.create_user(username='user1', password='12345')
        self.user2 = User.objects.create_user(username='user2', password='12345')

    def test_hit_count(self):
        # with one user
        self.app.set_user(self.user1)
        resp = self.app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': self.hit_count.pk}, xhr=True)
        self.assertEqual(resp.content, b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}')
        self.assertEqual(HitCount.objects.get(pk=self.hit_count.pk).hits, 1)

        # with the same user
        resp = self.app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': self.hit_count.pk}, xhr=True)
        self.assertEqual(resp.content,
                         b'{"hit_counted": false, "hit_message": "Not counted: authenticated user has active hit"}')
        self.assertEqual(HitCount.objects.get(pk=self.hit_count.pk).hits, 1)

        # with another user
        self.app.set_user(self.user2)
        resp = self.app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': self.hit_count.pk}, xhr=True)
        self.assertEqual(resp.content, b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}')
        self.assertEqual(HitCount.objects.get(pk=self.hit_count.pk).hits, 2)
