from typing import Callable

import pytest
from django.contrib.contenttypes.models import ContentType

from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import RepresentativeFactory
from vitrina.orgs.models import Organization
from vitrina.orgs.services import Role
from vitrina.uapi.models import Agent, RequestHistory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


@pytest.fixture
def representative_user(organization: Organization) -> User:
    user = UserFactory(is_staff=True)
    content_type = ContentType.objects.get_for_model(organization)
    RepresentativeFactory(user=user, content_type=content_type, object_id=organization.pk, role=Role.COORDINATOR)
    return user


@pytest.fixture
def data_service(organization: Organization) -> Dataset:
    return DatasetFactory(service=True, organization=organization)


@pytest.fixture
def agent(organization: Organization, data_service: Dataset) -> Agent:
    return Agent.objects.create(title="Agent", organization=organization, service=data_service)


@pytest.fixture
def request_history(agent: Agent) -> RequestHistory:
    return RequestHistory.objects.create(
        agent=agent,
        endpoint="/api/v1/resource",
        method="GET",
        http_result=200,
        result="SUCCESS",
        error="Error\nerror",
    )
