import pytest
from django.contrib.contenttypes.models import ContentType
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.likes.models import Like
from vitrina.requests.factories import RequestFactory
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


