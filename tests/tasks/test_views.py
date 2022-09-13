from datetime import datetime

import pytest
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina.orgs.factories import OrganizationFactory
from vitrina.tasks.factories import TaskFactory
from vitrina.users.models import User


@pytest.fixture
def set_up_data():
    organization = OrganizationFactory()
    user = User.objects.create_user(
        email="user1@test.com",
        password="test123"
    )
    user_with_role = User.objects.create(
        email="user2@test.com",
        password="test123",
        role='supervisor'
    )
    user_with_organization = User.objects.create(
        email="user3@test.com",
        password="test123",
        organization=organization
    )
    user_with_role_and_organization = User.objects.create(
        email="user4@test.com",
        password="test123",
        organization=organization,
        role='supervisor'
    )
    task_for_user = TaskFactory(user=user)
    task_for_role = TaskFactory(role='supervisor', created=datetime(2022, 8, 22, 10, 30))
    task_for_organization = TaskFactory(organization=organization, created=datetime(2022, 8, 23, 11, 30))
    return {
        'organization': organization,
        'user': user,
        'user_with_role': user_with_role,
        'user_with_organization': user_with_organization,
        'user_with_role_and_organization': user_with_role_and_organization,
        'task_for_user': task_for_user,
        'task_for_role': task_for_role,
        'task_for_organization': task_for_organization
    }


@pytest.mark.django_db
def test_task_list_without_role_and_organization(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data['user'])
    resp = app.get(reverse("user-task-list", kwargs={'pk': set_up_data['user'].pk}))
    assert list(resp.context["object_list"]) == [set_up_data['task_for_user']]


@pytest.mark.django_db
def test_task_list_with_role(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data['user_with_role'])
    resp = app.get(reverse("user-task-list", kwargs={'pk': set_up_data['user_with_role'].pk}))
    assert list(resp.context["object_list"]) == [set_up_data['task_for_role']]


@pytest.mark.django_db
def test_task_list_with_organization(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data['user_with_organization'])
    resp = app.get(reverse("user-task-list", kwargs={'pk': set_up_data['user_with_organization'].pk}))
    assert list(resp.context["object_list"]) == [set_up_data['task_for_organization']]


@pytest.mark.django_db
def test_task_list_with_role_and_organization(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data['user_with_role_and_organization'])
    resp = app.get(reverse("user-task-list", kwargs={'pk': set_up_data['user_with_role_and_organization'].pk}))
    assert list(resp.context["object_list"]) == [
        set_up_data['task_for_organization'],
        set_up_data['task_for_role']
    ]

