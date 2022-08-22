from datetime import datetime

import pytest
from django.urls import reverse
from django.test import Client

from django_webtest import DjangoTestApp

from vitrina.orgs.factories import OrganizationFactory
from vitrina.tasks.factories import TaskFactory
from vitrina.users.models import User


@pytest.fixture
def set_up_data():
    client = Client()
    organization = OrganizationFactory()
    user = User.objects.create(version=1, suspended=False, disabled=False, needs_password_change=False)
    user_with_role = User.objects.create(version=1, suspended=False, disabled=False, needs_password_change=False,
                                         role='supervisor')
    user_with_organization = User.objects.create(version=1, suspended=False, disabled=False,
                                                 needs_password_change=False, organization=organization)
    user_with_role_and_organization = User.objects.create(version=1, suspended=False, disabled=False,
                                                          needs_password_change=False, organization=organization,
                                                          role='supervisor')
    task_for_user = TaskFactory(user=user)
    task_for_role = TaskFactory(role='supervisor', created=datetime(2022, 8, 22, 10, 30))
    task_for_organization = TaskFactory(organization=organization, created=datetime(2022, 8, 23, 11, 30))
    return {
        'client': client,
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
def test_task_list_with_non_existing_user(app: DjangoTestApp, set_up_data):
    resp = set_up_data['client'].get(reverse("user-task-list", kwargs={'pk': 100}))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_task_list_without_role_and_organization(app: DjangoTestApp, set_up_data):
    resp = set_up_data['client'].get(reverse("user-task-list", kwargs={'pk': set_up_data['user'].pk}))
    assert len(resp.context["object_list"]) == 1
    assert resp.context["object_list"][0].pk == set_up_data['task_for_user'].pk


@pytest.mark.django_db
def test_task_list_with_role(app: DjangoTestApp, set_up_data):
    resp = set_up_data['client'].get(reverse("user-task-list",
                                             kwargs={'pk': set_up_data['user_with_role'].pk}))
    assert len(resp.context["object_list"]) == 1
    assert resp.context["object_list"][0].pk == set_up_data['task_for_role'].pk


@pytest.mark.django_db
def test_task_list_with_organization(app: DjangoTestApp, set_up_data):
    resp = set_up_data['client'].get(reverse("user-task-list",
                                             kwargs={'pk': set_up_data['user_with_organization'].pk}))
    assert len(resp.context["object_list"]) == 1
    assert resp.context["object_list"][0].pk == set_up_data['task_for_organization'].pk


@pytest.mark.django_db
def test_task_list_with_role_and_organization(app: DjangoTestApp, set_up_data):
    resp = set_up_data['client'].get(reverse("user-task-list",
                                             kwargs={'pk': set_up_data['user_with_role_and_organization'].pk}))
    assert len(resp.context["object_list"]) == 2
    assert resp.context["object_list"][0].pk == set_up_data['task_for_organization'].pk
    assert resp.context["object_list"][1].pk == set_up_data['task_for_role'].pk

