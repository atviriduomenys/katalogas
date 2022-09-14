from datetime import datetime

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.datasets.factories import DatasetFactory, DatasetMemberFactory
from vitrina.datasets.models import DatasetMember
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.users.models import User


@pytest.mark.django_db
def test_dataset_members_view_no_login(app: DjangoTestApp):
    dataset = DatasetFactory()
    resp = app.get(dataset.get_members_url())
    assert "/login/" in resp.location


@pytest.mark.django_db
def test_dataset_members_view_bad_login(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    dataset = DatasetFactory()
    resp = app.get(dataset.get_members_url(), expect_errors=True)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dataset_members_view_without_members(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    dataset = DatasetFactory()
    RepresentativeFactory(organization_id=dataset.organization.pk, email=user.email)
    resp = app.get(dataset.get_members_url())
    assert resp.status_code == 200
    assert list(resp.context['object_list']) == []


@pytest.mark.django_db
def test_dataset_members_view_with_members(app: DjangoTestApp):
    user = User.objects.create_user(email="test@test.com", password="test123")
    app.set_user(user)
    dataset = DatasetFactory()
    RepresentativeFactory(organization_id=dataset.organization.pk, email=user.email)
    member1 = DatasetMemberFactory(organization_id=dataset.organization.pk,
                                   role=DatasetMember.CREATOR, dataset=dataset, user=user)
    member2 = DatasetMemberFactory(organization_id=dataset.organization.pk,
                                   role=DatasetMember.PUBLISHER, dataset=dataset, user=user)

    resp = app.get(dataset.get_members_url())
    assert resp.status_code == 200
    assert list(resp.context['object_list']) == [member1, member2]
