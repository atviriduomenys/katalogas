import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import Client

from django_webtest import DjangoTestApp
from hitcount.models import HitCount

from vitrina.datasets.factories import DatasetFactory
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory


@pytest.mark.django_db
def test_view_count_dataset(app: DjangoTestApp):
    dataset = DatasetFactory()
    hit_count = HitCount.objects.create(content_object=dataset)

    client = Client()
    user1 = User.objects.create_user(username='user1', password='12345')
    user2 = User.objects.create_user(username='user2', password='12345')

    client.force_login(user1)

    # visit with one user
    resp = client.post(reverse('hitcount:hit_ajax'), data={'hitcountPK': hit_count.pk},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with the same user
    resp = client.post(reverse('hitcount:hit_ajax'), data={'hitcountPK': hit_count.pk},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.content == b'{"hit_counted": false, "hit_message": "Not counted: authenticated user has active hit"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with another user
    client.force_login(user2)
    resp = client.post(reverse('hitcount:hit_ajax'), data={'hitcountPK': hit_count.pk},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 2


@pytest.mark.django_db
def test_view_count_request(app: DjangoTestApp):
    request = RequestFactory()
    hit_count = HitCount.objects.create(content_object=request)

    client = Client()
    user1 = User.objects.create_user(username='user1', password='12345')
    user2 = User.objects.create_user(username='user2', password='12345')

    client.force_login(user1)

    # visit with one user
    resp = client.post(reverse('hitcount:hit_ajax'), data={'hitcountPK': hit_count.pk},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with the same user
    resp = client.post(reverse('hitcount:hit_ajax'), data={'hitcountPK': hit_count.pk},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.content == b'{"hit_counted": false, "hit_message": "Not counted: authenticated user has active hit"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with another user
    client.force_login(user2)
    resp = client.post(reverse('hitcount:hit_ajax'), data={'hitcountPK': hit_count.pk},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 2


@pytest.mark.django_db
def test_view_count_project(app: DjangoTestApp):
    project = ProjectFactory()

    hit_count = HitCount.objects.create(content_object=project)

    client = Client()
    user1 = User.objects.create_user(username='user1', password='12345')
    user2 = User.objects.create_user(username='user2', password='12345')

    client.force_login(user1)

    # visit with one user
    resp = client.post(reverse('hitcount:hit_ajax'), data={'hitcountPK': hit_count.pk},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with the same user
    resp = client.post(reverse('hitcount:hit_ajax'), data={'hitcountPK': hit_count.pk},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.content == b'{"hit_counted": false, "hit_message": "Not counted: authenticated user has active hit"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with another user
    client.force_login(user2)
    resp = client.post(reverse('hitcount:hit_ajax'), data={'hitcountPK': hit_count.pk},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 2
