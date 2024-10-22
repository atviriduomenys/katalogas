import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp
from hitcount.models import HitCount

from vitrina.datasets.factories import DatasetFactory
from vitrina.projects.factories import ProjectFactory
from vitrina.requests.factories import RequestFactory
from vitrina.users.models import User


@pytest.mark.django_db
def test_view_count_dataset(app: DjangoTestApp):
    dataset = DatasetFactory()
    hit_count = HitCount.objects.create(content_object=dataset)

    user1 = User.objects.create_user(email='user1@test.com', password='12345')
    user2 = User.objects.create_user(email='user2@test.com', password='12345')

    app.set_user(user1)

    # visit with one user
    resp = app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': hit_count.pk}, xhr=True)
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with the same user
    resp = app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': hit_count.pk}, xhr=True)
    assert resp.content == b'{"hit_counted": false, "hit_message": "Not counted: authenticated user has active hit"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with another user
    app.set_user(user2)
    resp = app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': hit_count.pk}, xhr=True)
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 2


@pytest.mark.django_db
def test_view_count_request(app: DjangoTestApp):
    request = RequestFactory()
    hit_count = HitCount.objects.create(content_object=request)

    user1 = User.objects.create_user(email='user1@test.com', password='12345')
    user2 = User.objects.create_user(email='user2@test.com', password='12345')

    app.set_user(user1)

    # visit with one user
    resp = app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': hit_count.pk}, xhr=True)
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with the same user
    resp = app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': hit_count.pk}, xhr=True)
    assert resp.content == b'{"hit_counted": false, "hit_message": "Not counted: authenticated user has active hit"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with another user
    app.set_user(user2)
    resp = app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': hit_count.pk}, xhr=True)
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 2


@pytest.mark.django_db
def test_view_count_project(app: DjangoTestApp):
    project = ProjectFactory()
    hit_count = HitCount.objects.create(content_object=project)

    user1 = User.objects.create_user(email='user1@test.com', password='12345')
    user2 = User.objects.create_user(email='user2@test.com', password='12345')

    app.set_user(user1)

    # visit with one user
    resp = app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': hit_count.pk}, xhr=True)
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with the same user
    resp = app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': hit_count.pk}, xhr=True)
    assert resp.content == b'{"hit_counted": false, "hit_message": "Not counted: authenticated user has active hit"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 1

    # visit with another user
    app.set_user(user2)
    resp = app.post(reverse('hitcount:hit_ajax'), {'hitcountPK': hit_count.pk}, xhr=True)
    assert resp.content == b'{"hit_counted": true, "hit_message": "Hit counted: user authentication"}'
    assert HitCount.objects.get(pk=hit_count.pk).hits == 2
