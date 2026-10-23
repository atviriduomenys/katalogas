import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
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
    return {"request": request, "dataset": dataset, "user": user}


@pytest.mark.django_db
def test_like_with_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True, access_rights=Dataset.PUBLIC)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    RepresentativeFactory(
        content_type=ContentType.objects.get_for_model(dataset),
        object_id=dataset.pk,
        user=user,
    )
    app.set_user(user)
    response = app.post(reverse("like", args=[ct.pk, dataset.pk, user.pk]))
    assert response.status_code == 302
    assert response.url == dataset.get_absolute_url()


@pytest.mark.django_db
def test_like_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.post(reverse("like", args=[ct.pk, dataset.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_unlike_with_non_public_dataset_without_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=False)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.post(reverse("unlike", args=[ct.pk, dataset.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_unlike_with_public_dataset_with_access(app: DjangoTestApp):
    dataset = DatasetFactory(is_public=True, access_rights=Dataset.PUBLIC)
    ct = ContentType.objects.get_for_model(dataset)
    user = UserFactory()
    app.set_user(user)
    response = app.post(reverse("unlike", args=[ct.pk, dataset.pk, user.pk]))
    assert response.status_code == 302
    assert response.url == dataset.get_absolute_url()


@pytest.mark.django_db
def test_like_with_not_approved_project_without_access(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    ct = ContentType.objects.get_for_model(project)
    user = UserFactory()
    app.set_user(user)
    response = app.post(reverse("like", args=[ct.pk, project.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_like_with_not_approved_project_with_access(app: DjangoTestApp):
    user = UserFactory(is_staff=True)
    project = ProjectFactory(status=Project.CREATED)
    ct = ContentType.objects.get_for_model(project)
    app.set_user(user)
    response = app.post(reverse("like", args=[ct.pk, project.pk, user.pk]))
    assert response.url == project.get_absolute_url()


@pytest.mark.django_db
def test_unlike_with_not_approved_project_without_access(app: DjangoTestApp):
    project = ProjectFactory(status=Project.CREATED)
    ct = ContentType.objects.get_for_model(project)
    user = UserFactory()
    app.set_user(user)
    response = app.post(reverse("unlike", args=[ct.pk, project.pk, user.pk]), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_unlike_with_not_approved_project_with_access(app: DjangoTestApp):
    user = UserFactory()
    project = ProjectFactory(status=Project.CREATED, user=user)
    ct = ContentType.objects.get_for_model(project)
    app.set_user(user)
    response = app.post(reverse("unlike", args=[ct.pk, project.pk, user.pk]))
    assert response.url == project.get_absolute_url()
