from http import HTTPStatus

import pytest
from django.urls import reverse
from django_webtest import DjangoTestApp
from vitrina.uapi import AgentType
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.uapi.models import Agent, RequestHistory
from vitrina.users.factories import UserFactory
from vitrina.users.models import User
from vitrina.uapi.factories import AgentFactory


pytestmark = pytest.mark.django_db


class TestAgentList:
    def test_success(self, app: DjangoTestApp, representative_user: User, organization: Organization):
        app.set_user(representative_user)

        another_organization = OrganizationFactory()
        agent_1 = AgentFactory(organization=organization)
        agent_2 = AgentFactory(organization=organization)
        archived_agent = AgentFactory(organization=organization, is_archived=True)
        different_organization_agent = AgentFactory(organization=another_organization)
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

        expected_keys = {"can_view_agents", "can_view_keys"}
        assert all(key in response.context for key in expected_keys)


class TestDetail:
    def test_sucess(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent: Agent,
    ):
        app.set_user(representative_user)
        url = reverse("agent-detail", args=[organization.pk, agent.pk])

        response = app.get(url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["agent"] == agent

    def test_archived_agent(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
    ):
        app.set_user(representative_user)
        agent = AgentFactory(organization=organization, is_archived=True)

        url = reverse("agent-detail", args=[organization.pk, agent.pk])
        response = app.get(url, expect_errors=True)

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestAgentCreate:
    def test_success(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
    ):
        app.set_user(representative_user)

        url = reverse("agent-create", args=[organization.pk])
        data = {
            "title": "Agent",
            "object_type": AgentType.SPINTA,
        }

        response = app.post(url, data)

        assert response.status_code == HTTPStatus.FOUND
        assert Agent.not_archived.count() == 1

        agent = Agent.not_archived.get(title=data["title"], organization=organization)

        assert agent.object_type == AgentType.SPINTA


class TestAgentUpdate:
    def test_success(self, app: DjangoTestApp, representative_user: User, organization: Organization, agent: Agent):
        app.set_user(representative_user)
        url = reverse("agent-update", args=[organization.pk, agent.pk])
        data = {
            "title": "Updated Agent Title",
            "object_type": AgentType.OTHER,
        }

        response = app.post(url, data)

        assert response.status_code == HTTPStatus.FOUND

        agent.refresh_from_db()
        assert agent.title == data["title"]
        assert agent.object_type == data["object_type"]


class TestAgentDelete:
    def test_success(self, app: DjangoTestApp, representative_user: User, organization: Organization, agent: Agent):
        app.set_user(representative_user)
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
        request_history: RequestHistory,
    ):
        app.set_user(representative_user)
        url = reverse("request-history", args=[organization.pk, request_history.pk])

        response = app.get(url)
        assert response.status_code == HTTPStatus.OK
        assert response.context["request_history"] == request_history
