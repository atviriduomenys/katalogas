import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.likes.models import Like
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.projects.factories import ProjectFactory
from vitrina.projects.models import Project
from vitrina.requests.factories import RequestFactory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


@pytest.fixture
def like_data():
    request = RequestFactory()
    dataset = DatasetFactory()
    user = User.objects.create_user(email="test@gmail.com", password="test123")
    return {
        'request': request,
        'dataset': dataset,
        'user': user
    }


@pytest.mark.django_db
def test_request_like_without_user(app: DjangoTestApp, like_data):
    resp = app.get(like_data['request'].get_absolute_url())
    assert Like.objects.count() == 0
    assert list(resp.html.find(id='request_likes').stripped_strings) == ['0']


@pytest.mark.django_db
def test_request_like_with_user(app: DjangoTestApp, like_data):
    app.set_user(like_data['user'])
    resp = app.get(like_data['request'].get_absolute_url())
    assert Like.objects.count() == 0
    assert list(resp.html.find(id='request_likes').stripped_strings) == ['0']
    assert resp.html.find(id='request_likes').find('input', {'type': 'submit'}).attrs['value'] == "Patinka"
    resp.forms['like-form'].submit()
    resp = app.get(like_data['request'].get_absolute_url())
    assert Like.objects.count() == 1
    assert list(resp.html.find(id='request_likes').stripped_strings) == ['1']
    assert resp.html.find(id='request_likes').find('input', {'type': 'submit'}).attrs['value'] == "Nepatinka"


@pytest.mark.django_db
def test_request_unlike(app: DjangoTestApp, like_data):
    Like.objects.create(
        content_type=ContentType.objects.get_for_model(like_data['request']),
        object_id=like_data['request'].pk,
        user=like_data['user']
    )
    app.set_user(like_data['user'])
    resp = app.get(like_data['request'].get_absolute_url())
    assert Like.objects.count() == 1
    assert list(resp.html.find(id='request_likes').stripped_strings) == ['1']
    assert resp.html.find(id='request_likes').find('input', {'type': 'submit'}).attrs['value'] == "Nepatinka"
    resp.forms['like-form'].submit()
    resp = app.get(like_data['request'].get_absolute_url())
    assert Like.objects.count() == 0
    assert list(resp.html.find(id='request_likes').stripped_strings) == ['0']
    assert resp.html.find(id='request_likes').find('input', {'type': 'submit'}).attrs['value'] == "Patinka"


@pytest.mark.django_db
def test_dataset_like_without_user(app: DjangoTestApp, like_data):
    resp = app.get(like_data['dataset'].get_absolute_url())
    assert list(resp.html.find(id='dataset_likes').stripped_strings) == ['0']


@pytest.mark.django_db
def test_dataset_like_with_user(app: DjangoTestApp, like_data):
    app.set_user(like_data['user'])
    resp = app.get(like_data['dataset'].get_absolute_url())
    assert list(resp.html.find(id='dataset_likes').stripped_strings) == ['0']
    assert resp.html.find(id='dataset_likes').find('input', {'type': 'submit'}).attrs['value'] == "Patinka"
    resp.forms['like-form'].submit()
    resp = app.get(like_data['dataset'].get_absolute_url())
    assert list(resp.html.find(id='dataset_likes').stripped_strings) == ['1']
    assert resp.html.find(id='dataset_likes').find('input', {'type': 'submit'}).attrs['value'] == "Nepatinka"


@pytest.mark.django_db
def test_dataset_unlike(app: DjangoTestApp, like_data):
    Like.objects.create(
        content_type=ContentType.objects.get_for_model(like_data['dataset']),
        object_id=like_data['dataset'].pk,
        user=like_data['user']
    )
    app.set_user(like_data['user'])
    resp = app.get(like_data['dataset'].get_absolute_url())
    assert Like.objects.count() == 1
    assert list(resp.html.find(id='dataset_likes').stripped_strings) == ['1']
    assert resp.html.find(id='dataset_likes').find('input', {'type': 'submit'}).attrs['value'] == "Nepatinka"
    resp.forms['like-form'].submit()
    resp = app.get(like_data['dataset'].get_absolute_url())
    assert Like.objects.count() == 0
    assert list(resp.html.find(id='dataset_likes').stripped_strings) == ['0']
    assert resp.html.find(id='dataset_likes').find('input', {'type': 'submit'}).attrs['value'] == "Patinka"


@pytest.mark.django_db
def test_like_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.post(reverse('like', args=[ct.pk, dataset.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_like_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
    )
    app.set_user(user)
    response = app.post(reverse('like', args=[ct.pk, dataset.pk, user.pk]))
    assert response.url == dataset.get_absolute_url()


@pytest.mark.django_db
def test_unlike_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.post(reverse('unlike', args=[ct.pk, dataset.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_unlike_with_non_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
    )
    app.set_user(user)
    response = app.post(reverse('unlike', args=[ct.pk, dataset.pk, user.pk]))
    assert response.url == dataset.get_absolute_url()


@pytest.mark.django_db
def test_like_with_not_approved_project_without_access(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    ct = ContentType.objects.get_for_model(project)
    user = UserFactory()
    app.set_user(user)
    response = app.post(reverse('like', args=[ct.pk, project.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_like_with_not_approved_project_with_access(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory(status=Project.CREATED)
    ct = ContentType.objects.get_for_model(project)
    app.set_user(user)
    response = app.post(reverse('like', args=[ct.pk, project.pk, user.pk]))
    assert response.url == project.get_absolute_url()


@pytest.mark.django_db
def test_unlike_with_not_approved_project_without_access(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    ct = ContentType.objects.get_for_model(project)
    user = UserFactory()
    app.set_user(user)
    response = app.post(reverse('unlike', args=[ct.pk, project.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_unlike_with_not_approved_project_with_access(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(status=Project.CREATED, user=user)
    ct = ContentType.objects.get_for_model(project)
    app.set_user(user)
    response = app.post(reverse('unlike', args=[ct.pk, project.pk, user.pk]))
    assert response.url == project.get_absolute_url()
