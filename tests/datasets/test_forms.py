from datetime import datetime
import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory
from vitrina.users.models import User


@pytest.mark.django_db
def test_change_form_no_login(app: DjangoTestApp):
    response = app.get(reverse('dataset-change', kwargs={'org_kind': 'test_org_kind',
                                                         'org_slug': 'test_org_slug',
                                                         'slug': 'test_dataset_slug'}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_change_form_wrong_login(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(reverse('dataset-change', kwargs={'org_kind': 'test_org_kind',
                                                         'org_slug': 'test_org_slug',
                                                         'slug': 'test_dataset_slug'}), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_change_form_correct_login(app: DjangoTestApp):
    dataset = DatasetFactory(
        title="dataset_title",
        title_en="dataset_title",
        published=datetime(2022, 9, 7),
        slug='test-dataset-slug',
        description='test description',
    )
    user = User.objects.create_user(email="test@test.com", password="test123",
                                    organization=dataset.organization)
    app.set_user(user)
    dataset.manager = user
    form = app.get(reverse('dataset-change', kwargs={'org_kind': dataset.organization.kind,
                                                     'org_slug': dataset.organization.slug,
                                                     'slug': dataset.slug})).forms['dataset-form']
    form['title'] = 'Edited title'
    form['description'] = 'edited dataset description'
    resp = form.submit()
    dataset.refresh_from_db()
    assert resp.status_code == 302
    assert resp.url == reverse('dataset-detail', kwargs={'slug': 'edited-title'})
    assert dataset.title == 'Edited title'
    assert dataset.description == 'edited dataset description'


@pytest.mark.django_db
def test_add_form_no_login(app: DjangoTestApp):
    response = app.get(reverse('dataset-add', kwargs={'org_kind': 'test_org_kind',
                                                      'slug': 'test_org_slug'}))
    assert response.status_code == 302
    assert settings.LOGIN_URL in response.location


@pytest.mark.django_db
def test_add_form_wrong_login(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    response = app.get(reverse('dataset-add', kwargs={'org_kind': 'test_org_kind',
                                                      'slug': 'test_org_slug'}), expect_errors=True)
    assert response.status_code == 403


@pytest.mark.django_db
def test_add_form_correct_login(app: DjangoTestApp):
    org = OrganizationFactory(
        title="Org_title",
        created=datetime(2022, 8, 22, 10, 30),
        jurisdiction="Jurisdiction1",
        slug='test-org-slug',
        kind='test_org_kind'
    )
    user = User.objects.create_user(email="test@test.com", password="test123",
                                    organization=org)
    app.set_user(user)
    form = app.get(reverse('dataset-add', kwargs={'org_kind': org.kind,
                                                  'slug': org.slug})).forms['dataset-form']
    form['title'] = 'Added title'
    form['description'] = 'Added new dataset description'
    form['manager'] = user.id
    resp = form.submit()
    assert Dataset.objects.filter(title="Added title").count() == 1
    assert resp.status_code == 302
    assert resp.url == reverse('dataset-detail', kwargs={'slug': 'added-title'})
