from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import DatasetMembers
from vitrina.orgs.factories import OrganizationFactory
from vitrina.users.models import User


@pytest.fixture
def members_data():
    org = OrganizationFactory(
        title="test organization",
        created=datetime(2022, 9, 22, 10, 30),
        jurisdiction="test_jurisdiction",
        kind='test_org_kind',
        slug='test_org_slug'
    )
    dataset = DatasetFactory(
        title="Testinis duomenų rinkinys",
        title_en="Test dataset",
        published=datetime(2022, 6, 1),
        organization=org,
        slug='test_dataset_slug'
    )
    return [dataset, org]


@pytest.fixture
def user():
    user = User.objects.create_user(email="test@test.com", password="test123")
    return user


@pytest.mark.django_db
def test_dataset_members_view_without_members(app: DjangoTestApp, members_data):
    resp = app.get(reverse('dataset-members', kwargs={'org_kind': 'test_org_kind',
                                                      'org_slug': 'test_org_slug',
                                                      'dataset_slug': 'test_dataset_slug'}))
    assert list(resp.context['object_list']) == []


@pytest.mark.django_db
def test_dataset_members_view_with_members(app: DjangoTestApp, members_data, user: User):
    member1 = DatasetMembers.objects.create(
        role='Creator',
        created=datetime.now(),
        contact=1,
        organization_id=members_data[1].pk,
        user_id=user.pk
    )
    member2 = DatasetMembers.objects.create(
        role='Publisher',
        created=datetime.now(),
        contact=1,
        organization_id=members_data[1].pk,
        user_id=user.pk
    )

    resp = app.get(reverse('dataset-members', kwargs={'org_kind': 'test_org_kind',
                                                      'org_slug': 'test_org_slug',
                                                      'dataset_slug': 'test_dataset_slug'}))
    assert list(resp.context['object_list']) == [member1, member2]
