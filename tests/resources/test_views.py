import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.factories import DatasetDistributionFactory
from vitrina.resources.models import DatasetDistribution
from vitrina.users.models import User


@pytest.mark.django_db
def test_change_form_wrong_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(reverse('resource-change', kwargs={'pk': resource.id}))
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location


@pytest.mark.django_db
def test_change_form_correct_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = User.objects.create_user(email="test@test.com", password="test123",
                                    organization=resource.dataset.organization)
    app.set_user(user)
    resource.dataset.manager = user
    form = app.get(reverse('resource-change', kwargs={'pk': resource.id})).forms['resource-form']
    form['title'] = 'Edited title'
    form['description'] = 'edited resource description'
    resp = form.submit()
    resource.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('dataset-detail', kwargs={'pk': resource.dataset_id})
    assert resource.title == 'Edited title'
    assert resource.description == 'edited resource description'


@pytest.mark.django_db
def test_click_edit_button(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = User.objects.create_user(email="test@test.com", password="test123",
                                    organization=resource.dataset.organization)
    app.set_user(user)
    resource.dataset.manager = user
    response = app.get(reverse('dataset-detail', kwargs={'pk': resource.dataset_id}))
    response.click(linkid='change_resource')
    assert response.status_code == 200


@pytest.mark.django_db
def test_add_form_no_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    response = app.get(reverse('resource-add', kwargs={'pk': resource.dataset_id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_add_form_wrong_login(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    resource = DatasetDistributionFactory()
    response = app.get(reverse('resource-add', kwargs={'pk': resource.dataset_id}))
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location


@pytest.mark.django_db
def test_add_form_correct_login(app: DjangoTestApp):
    dataset = DatasetFactory()
    user = User.objects.create_user(email="test@test.com", password="test123",
                                    organization=dataset.organization)
    app.set_user(user)
    dataset.manager = user
    form = app.get(reverse('resource-add', kwargs={'pk': dataset.pk})).forms['resource-form']
    form['title'] = 'Added title'
    form['description'] = 'Added new resource description'
    form['download_url'] = "www.google.lt"
    resp = form.submit()
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 1


@pytest.mark.django_db
def test_click_add_button(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = User.objects.create_user(email="test@test.com", password="test123",
                                    organization=resource.dataset.organization)
    app.set_user(user)
    response = app.get(reverse('dataset-detail', kwargs={'pk': resource.dataset_id}))
    response.click(linkid='add_resource')
    assert response.status_code == 200


@pytest.mark.django_db
def test_delete_no_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    response = app.get(reverse('resource-delete', kwargs={'pk': resource.id}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_delete_wrong_login(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    resource = DatasetDistributionFactory()
    response = app.get(reverse('resource-delete', kwargs={'pk': resource.id}))
    assert response.status_code == 302
    assert str(resource.dataset_id) in response.location


@pytest.mark.django_db
def test_delete_correct_login(app: DjangoTestApp):
    resource = DatasetDistributionFactory(title='base title', description='base description')
    user = User.objects.create_user(email="test@test.com", password="test123",
                                    organization=resource.dataset.organization)
    app.set_user(user)
    resource.dataset.manager = user
    resp = app.get(reverse('resource-delete', kwargs={'pk': resource.pk}))
    assert resp.status_code == 302
    assert DatasetDistribution.objects.filter().count() == 0


@pytest.mark.django_db
def test_click_delete_button(app: DjangoTestApp):
    resource = DatasetDistributionFactory()
    user = User.objects.create_user(email="test@test.com", password="test123",
                                    organization=resource.dataset.organization)
    app.set_user(user)
    response = app.get(reverse('dataset-detail', kwargs={'pk': resource.dataset_id}))
    response.click(linkid='delete_resource')
    assert response.status_code == 200
