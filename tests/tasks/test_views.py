from datetime import datetime

import pytest
import pytz
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from django_webtest import DjangoTestApp

from vitrina import settings
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.tasks.factories import TaskFactory
from vitrina.users.models import User

timezone = pytz.timezone(settings.TIME_ZONE)


@pytest.fixture
def set_up_data():
    organization = OrganizationFactory()
    content_type = ContentType.objects.get_for_model(organization)
    user = User.objects.create_user(
        email="user1@test.com",
        password="test123"
    )
    user_with_organization = User.objects.create(
        email="user3@test.com",
        password="test123",
        organization=organization
    )
    RepresentativeFactory(
        user=user_with_organization,
        content_type=content_type,
        object_id=organization.pk
    )
    task_for_user = TaskFactory(user=user)
    task_for_organization = TaskFactory(organization=organization,
                                        created=timezone.localize(datetime(2022, 8, 23, 11, 30)))
    return {
        'organization': organization,
        'user': user,
        'user_with_organization': user_with_organization,
        'task_for_user': task_for_user,
        'task_for_organization': task_for_organization
    }


@pytest.mark.django_db
def test_task_list_with_user(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data['user'])
    resp = app.get('%s?filter=user' % reverse("user-task-list", kwargs={'pk': set_up_data['user'].pk}))
    assert list(resp.context["object_list"]) == [set_up_data['task_for_user']]


@pytest.mark.django_db
def test_task_list_with_organization(app: DjangoTestApp, set_up_data):
    app.set_user(set_up_data['user_with_organization'])
    resp = app.get('%s?filter=all' % reverse("user-task-list", kwargs={'pk': set_up_data['user_with_organization'].pk}))
    assert list(resp.context["object_list"]) == [set_up_data['task_for_organization']]
