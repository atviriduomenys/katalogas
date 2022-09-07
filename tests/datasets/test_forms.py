from datetime import datetime
import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from django.contrib.auth.models import User


@pytest.fixture
def data():
    dataset = DatasetFactory(
        title="dataset_title",
        title_en="dataset_title",
        published=datetime(2022, 9, 7),
        slug='test_dataset_slug',
    )
    organization = OrganizationFactory(
        title="Org_title",
        created=datetime(2022, 8, 22, 10, 30),
        jurisdiction="Jurisdiction1",
        slug='test_org_slug',
    )


@pytest.mark.django_db
def test_change_form_no_login(app: DjangoTestApp, data):
    response = app.get(reverse('dataset-change', kwargs={'org_slug': 'test_org_slug',
                                                         'dataset_slug': 'test_dataset_slug'}))
    assert response.status_code == 302
    assert response.location == '/dataset/test_org_slug/'


@pytest.mark.django_db
def test_change_form_wrong_login(app: DjangoTestApp, data):
    test_user = User.objects.create_user(username='test_user', password='12345')
    app.set_user(test_user)
    response = app.get(reverse('dataset-change', kwargs={'org_slug': 'test_org_slug',
                                                                     'dataset_slug': 'test_dataset_slug'}))
    assert response.status_code == 302
    assert response.location == '/dataset/test_org_slug/'
