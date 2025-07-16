import secrets
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django_webtest import DjangoTestApp

from vitrina.api.models import ApiKey
from vitrina.datasets.factories import DatasetFactory
from vitrina.datasets.models import Dataset
from vitrina.uapi import AgentType
from vitrina.orgs.factories import OrganizationFactory, RepresentativeFactory
from vitrina.orgs.models import Organization
from vitrina.uapi.models import Agent
from vitrina.orgs.services import Role, hash_api_key
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


@pytest.fixture
def organization() -> Organization:
    return OrganizationFactory()


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


@pytest.mark.django_db
def test_list_view(app: DjangoTestApp, representative_user: User, organization: Organization):
    app.set_user(representative_user)

    another_organization = OrganizationFactory()
    dataset = DatasetFactory(service=True, organization=organization)
    agent_1 = Agent.objects.create(title="Agent 1", organization=organization, service=dataset)
    agent_2 = Agent.objects.create(title="Agent 2", organization=organization, service=dataset)
    archived_agent = Agent.objects.create(title="Agent 3", organization=organization, service=dataset, is_archived=True)
    different_organization_agent = Agent.objects.create(
        title="Agent 4", organization=another_organization, service=dataset
    )
    url = reverse("agent-list", args=[organization.pk])

    response = app.get(url)

    assert response.status_code == HTTPStatus.OK
    returned_agents = response.context["agents"]
    assert agent_1 in returned_agents
    assert agent_2 in returned_agents
    assert archived_agent not in returned_agents
    assert different_organization_agent not in returned_agents


@pytest.mark.django_db
def test_detail_view(
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent: Agent,
        data_service: Dataset
):
    app.set_user(representative_user)
    url = reverse("agent-detail", args=[organization.pk, agent.pk])

    response = app.get(url)

    assert response.status_code == HTTPStatus.OK
    assert response.context["agent"] == agent
    assert response.context["dataset"] == data_service
    assert not response.context["raw_api_key"]


@pytest.mark.django_db
def test_detail_view_archived_agent(app: DjangoTestApp, representative_user: User, organization: Organization):
    app.set_user(representative_user)
    dataset = DatasetFactory(service=True, organization=organization)
    agent = Agent.objects.create(title="Agent", organization=organization, service=dataset, is_archived=True)

    url = reverse("agent-detail", args=[organization.pk, agent.pk])
    response = app.get(url, expect_errors=True)

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
def test_create_view(app: DjangoTestApp, representative_user: User, organization: Organization):
    app.set_user(representative_user)

    url = reverse("agent-create", args=[organization.pk])
    data = {
        "title": "Agent",
        "is_enabled": True,
        "is_open_data_published": True,
        "object_type": AgentType.SPINTA,
        "open_data_publish_url": "https://data.gov.lt"
    }

    response = app.post(url, data)

    assert response.status_code == HTTPStatus.FOUND
    assert Agent.objects.count() == 1
    agent = Agent.objects.filter(title=data["title"], organization=organization).first()
    assert agent is not None
    assert ApiKey.objects.count() == 1
    assert hash_api_key(app.session["new_agent_api_key"]) == ApiKey.objects.filter(agent=agent).first().api_key


@pytest.mark.django_db
def test_create_agent_transaction_rollback_on_error(app, representative_user, organization):
    app.set_user(representative_user)

    url = reverse("agent-create", args=[organization.pk])
    data = {
        "title": "New Agent",
        "is_enabled": True,
        "is_open_data_published": False,
        "object_type": "other",
        "open_data_publish_url": "https://data.gov.lt/agent",
    }

    with patch("vitrina.uapi.views.ApiKey.objects.create", side_effect=Exception("Simulated error")):
        response = app.post(url, data)

    assert response.status_code == HTTPStatus.OK  # Re-rendered due to `form_invalid()`.
    assert Agent.objects.count() == 0
    assert Dataset.objects.filter(service=True, translations__title__icontains="Agento").count() == 0
    assert ApiKey.objects.count() == 0


@pytest.mark.django_db
def test_update_view(app: DjangoTestApp, representative_user: User, organization: Organization, agent: Agent):
    app.set_user(representative_user)
    url = reverse("agent-update", args=[organization.pk, agent.pk])
    data = {
        "title": "Updated Agent Title",
        "is_enabled": True,
        "is_open_data_published": False,
        "object_type": AgentType.OTHER,
        "open_data_publish_url": "https://updated-data.gov.lt",
    }

    response = app.post(url, data)

    assert response.status_code == HTTPStatus.FOUND

    agent.refresh_from_db()
    assert agent.title == data["title"]
    assert agent.is_enabled is data["is_enabled"]
    assert agent.is_open_data_published is data["is_open_data_published"]
    assert agent.object_type == data["object_type"]
    assert agent.open_data_publish_url == data["open_data_publish_url"]


@pytest.mark.django_db
def test_delete_view(app: DjangoTestApp, representative_user: User, organization: Organization, agent: Agent):
    app.set_user(representative_user)
    ApiKey.objects.create(api_key=hash_api_key(secrets.token_urlsafe()), enabled=True, agent=agent)
    url = reverse("agent-delete", args=[organization.pk, agent.pk])

    response = app.post(url)

    assert response.status_code == HTTPStatus.FOUND
    assert Agent.objects.count() == 1
    agent = Agent.objects.first()
    assert agent.is_archived is True
    assert agent.apikey.deleted is True
    assert agent.apikey.deleted_on is not None
