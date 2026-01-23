import secrets
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from vitrina.api.models import ApiKey
from vitrina.datasets.factories import DatasetFactory, AgentFactory
from vitrina.datasets.models import Dataset, DCATResourceSubclass
from vitrina.uapi import AgentType, Environment
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.uapi.models import Agent, RequestHistory
from vitrina.orgs.services import hash_api_key
from vitrina.users.factories import UserFactory
from vitrina.users.models import User


pytestmark = pytest.mark.django_db


class TestAgentList:
    def test_success(self, app: DjangoTestApp, representative_user: User, organization: Organization):
        app.set_user(representative_user)

        another_organization = OrganizationFactory()
        dataset = DatasetFactory(service=True, organization=organization)
        agent_1 = Agent.objects.create(title="Agent 1", organization=organization, service=dataset)
        agent_2 = Agent.objects.create(title="Agent 2", organization=organization, service=dataset)
        archived_agent = Agent.objects.create(
            title="Agent 3", organization=organization, service=dataset, is_archived=True
        )
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

    def test_agent_view_exposes_can_view_agents_flag(
        self,
        app: DjangoTestApp,
    ):
        organization = OrganizationFactory()
        user = UserFactory(is_staff=True)

        app.set_user(user)
        response = app.get(reverse("agent-list", args=[organization.pk]))

        assert "can_view_agents" in response.context
        assert "can_view_keys" in response.context


class TestDetail:
    def test_sucess(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent: Agent,
        data_service: Dataset,
    ):
        app.set_user(representative_user)
        url = reverse("agent-detail", args=[organization.pk, agent.pk])

        response = app.get(url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["agent"] == agent
        assert response.context["dataset"] == data_service
        assert not response.context["secret"]

    def test_archived_agent(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
    ):
        app.set_user(representative_user)
        dataset = DatasetFactory(service=True, organization=organization)
        agent = Agent.objects.create(title="Agent", organization=organization, service=dataset, is_archived=True)

        url = reverse("agent-detail", args=[organization.pk, agent.pk])
        response = app.get(url, expect_errors=True)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_agent_detail_view_request_history(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent: Agent,
        data_service: Dataset,
        request_history: RequestHistory,
    ):
        app.set_user(representative_user)
        url = reverse("agent-detail", args=[organization.pk, agent.pk])

        response = app.get(url)

        assert response.status_code == HTTPStatus.OK
        assert list(response.context["agent"].requesthistory.all()) == [request_history]
        assert response.context["agent"] == agent
        assert response.context["dataset"] == data_service
        assert not response.context["secret"]

    def test_wrong_agent_detail_view_request_history_(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent: Agent,
        data_service: Dataset,
        request_history: RequestHistory,
    ):
        """Request_history is created for an agent which is not the one making the request."""

        another_agent = AgentFactory()
        app.set_user(representative_user)
        url = reverse("agent-detail", args=[another_agent.organization.pk, another_agent.pk])

        response = app.get(url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["agent"] == another_agent
        assert not response.context["secret"]
        assert list(response.context["agent"].requesthistory.all()) == []


class TestAgentCreate:
    @pytest.mark.parametrize(
        "service_provided",
        [
            False,
            True,
        ],
        ids=["no_service_provided", "service_provided"],
    )
    def test_success(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        service_provided: bool,
    ):
        app.set_user(representative_user)

        organization_service = None
        mocked_id = "some-id"
        url = reverse("agent-create", args=[organization.pk])
        data = {
            "title": "Agent",
            "is_enabled": True,
            "environment": Environment.DEVELOPMENT,
            "is_open_data_published": True,
            "object_type": AgentType.SPINTA,
            "open_data_publish_url": "https://data.gov.lt",
            "auth_server_url": "https://auth.example.com",
            "api_gate_server_url": "https://api-gate.example.com",
            "agent_address": "https://agent.example.com",
        }

        if service_provided:
            organization_service = DatasetFactory(
                service=True,
                organization=organization,
                subclass=DCATResourceSubclass.objects.get(name=DCATResourceSubclass.SERVICE),
                metadata=data["title"].lower().replace(" ", "_"),
            )
            data["service"] = organization_service.pk

        with patch(
            "vitrina.uapi.views.template_views.OAuthClientManagement.create_oauth_client",
            return_value=(mocked_id, "some-secret"),
        ) as mock_create_oauth_client:
            response = app.post(url, data)

        assert response.status_code == HTTPStatus.FOUND
        assert Agent.objects.count() == 1
        assert mock_create_oauth_client.called

        agent = Agent.objects.filter(title=data["title"], organization=organization).first()
        agent_service = agent.service

        assert agent.oauth_client_id == mocked_id
        assert agent.auth_server_url == data["auth_server_url"]
        assert agent.api_gate_server_url == data["api_gate_server_url"]
        assert agent.agent_address == data["agent_address"]
        assert agent.is_enabled is data["is_enabled"]
        assert agent.environment == data["environment"]
        assert agent_service.service is True
        assert agent_service.subclass == DCATResourceSubclass.objects.get(name=DCATResourceSubclass.SERVICE)
        assert agent_service.metadata.first().name == Agent().get_codename(data["title"])

        if service_provided:
            assert agent_service == organization_service
        else:
            assert agent_service != organization_service

    def test_transaction_rollback_on_error(
        self,
        app,
        representative_user,
        organization,
    ):
        app.set_user(representative_user)

        url = reverse("agent-create", args=[organization.pk])
        data = {
            "title": "New Agent",
            "is_enabled": True,
            "is_open_data_published": False,
            "object_type": "other",
            "open_data_publish_url": "https://data.gov.lt/agent",
        }

        with patch(
            "vitrina.uapi.views.template_views.OAuthClientManagement.create_oauth_client",
            side_effect=Exception("Simulated error"),
        ):
            response = app.post(url, data)

        assert response.status_code == HTTPStatus.OK  # Re-rendered due to `form_invalid()`.
        assert Agent.objects.count() == 0
        assert Dataset.objects.filter(service=True, translations__title__icontains="Agento").count() == 0
        assert ApiKey.objects.count() == 0


class TestAgentUpdate:
    def test_success(self, app: DjangoTestApp, representative_user: User, organization: Organization, agent: Agent):
        app.set_user(representative_user)
        url = reverse("agent-update", args=[organization.pk, agent.pk])
        data = {
            "title": "Updated Agent Title",
            "is_enabled": True,
            "environment": Environment.TESTING,
            "is_open_data_published": False,
            "object_type": AgentType.OTHER,
            "open_data_publish_url": "https://updated-data.gov.lt",
            "service": agent.service.pk,
            "agent_address": "https://updated-agent.gov.lt",
            "auth_server_url": "https://updated-auth.gov.lt",
            "api_gate_server_url": "https://updated-api-gate.gov.lt",
        }

        response = app.post(url, data)

        assert response.status_code == HTTPStatus.FOUND

        agent.refresh_from_db()
        assert agent.title == data["title"]
        assert agent.is_enabled is data["is_enabled"]
        assert agent.is_open_data_published is data["is_open_data_published"]
        assert agent.object_type == data["object_type"]
        assert agent.environment == data["environment"]
        assert agent.open_data_publish_url == data["open_data_publish_url"]
        assert agent.agent_address == data["agent_address"]
        assert agent.auth_server_url == data["auth_server_url"]
        assert agent.api_gate_server_url == data["api_gate_server_url"]


class TestAgentDelete:
    def test_success(self, app: DjangoTestApp, representative_user: User, organization: Organization, agent: Agent):
        app.set_user(representative_user)
        ApiKey.objects.create(api_key=hash_api_key(secrets.token_urlsafe()), enabled=True, agent=agent)
        url = reverse("agent-delete", args=[organization.pk, agent.pk])

        response = app.post(url)

        assert response.status_code == HTTPStatus.FOUND
        assert Agent.objects.count() == 1
        agent = Agent.objects.first()
        assert agent.is_archived is True


class TestRequestHistoryDetail:
    def test_success(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        data_service: Dataset,
        agent: Agent,
        request_history: RequestHistory,
    ):
        app.set_user(representative_user)
        url = reverse("request-history", args=[organization.pk, agent.pk, request_history.pk])

        response = app.get(url)
        assert response.status_code == HTTPStatus.OK
        assert response.context["request_history"] == request_history
