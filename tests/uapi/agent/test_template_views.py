from http import HTTPStatus
from unittest.mock import patch

import pytest
from _pytest.fixtures import FixtureRequest
from django.urls import reverse, resolve
from django_webtest import DjangoTestApp
from vitrina.uapi import AgentType
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Organization
from vitrina.uapi.models import Agent, RequestHistory, Environment, AgentEnvironment
from vitrina.users.factories import UserFactory
from vitrina.users.models import User
from vitrina.uapi.factories import AgentFactory, AgentEnvironmentFactory


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

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(reverse("agent-list", args=[organization.pk]), expect_errors=True)

        assert response.status_code == expected_status

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization):
        breadcrumb_url_names_expected = ["home", "organization-list", "organization-detail"]

        url = reverse("agent-list", args=[organization.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected


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

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
        agent: Agent,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(reverse("agent-detail", args=[organization.pk, agent.pk]), expect_errors=True)

        assert response.status_code == expected_status

    def test_archived_agent_env_not_displayed(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent: Agent,
    ):
        app.set_user(representative_user)
        url = reverse("agent-detail", args=[organization.pk, agent.pk])
        archived_env = AgentEnvironmentFactory(agent=agent, is_archived=True)

        response = app.get(url)

        assert response.status_code == HTTPStatus.OK
        context_agent: Agent = response.context["agent"]
        context_environments = response.context["environments"]
        assert context_agent == agent
        assert archived_env not in context_environments

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization, agent: Agent):
        breadcrumb_url_names_expected = ["home", "organization-list", "organization-detail", "agent-list"]

        url = reverse("agent-detail", args=[organization.pk, agent.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected


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

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(reverse("agent-create", args=[organization.pk]), expect_errors=True)

        assert response.status_code == expected_status

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization):
        breadcrumb_url_names_expected = ["home", "organization-list", "organization-detail", "agent-list"]

        url = reverse("agent-create", args=[organization.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected


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

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
        agent: Agent,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(reverse("agent-update", args=[organization.pk, agent.pk]), expect_errors=True)

        assert response.status_code == expected_status

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization, agent: Agent):
        breadcrumb_url_names_expected = [
            "home",
            "organization-list",
            "organization-detail",
            "agent-list",
            "agent-detail",
        ]

        url = reverse("agent-update", args=[organization.pk, agent.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected


class TestAgentDelete:
    def test_success(self, app: DjangoTestApp, representative_user: User, organization: Organization, agent: Agent):
        app.set_user(representative_user)
        url = reverse("agent-delete", args=[organization.pk, agent.pk])

        response = app.post(url)

        assert response.status_code == HTTPStatus.FOUND
        agent.refresh_from_db()
        assert agent.is_archived is True

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
        agent: Agent,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(reverse("agent-delete", args=[organization.pk, agent.pk]), expect_errors=True)

        assert response.status_code == expected_status

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization, agent: Agent):
        breadcrumb_url_names_expected = [
            "home",
            "organization-list",
            "organization-detail",
            "agent-list",
            "agent-detail",
        ]

        url = reverse("agent-delete", args=[organization.pk, agent.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected


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

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
        request_history: RequestHistory,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(reverse("request-history", args=[organization.pk, request_history.pk]), expect_errors=True)

        assert response.status_code == expected_status

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization, request_history: RequestHistory):
        breadcrumb_url_names_expected = [
            "home",
            "organization-list",
            "organization-detail",
            "agent-list",
            "agent-detail",
            "agent-env-detail",
        ]

        url = reverse("request-history", args=[organization.pk, request_history.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected


class TestAgentEnvCreate:
    def test_success(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent: Agent,
    ):
        app.set_user(representative_user)

        mocked_id = "some-id"
        url = reverse("agent-env-create", args=[organization.pk, agent.pk])
        data = {
            "is_enabled": True,
            "environment": Environment.DEVELOPMENT,
            "is_open_data_published": True,
            "open_data_publish_url": "https://data.gov.lt",
            "auth_server_url": "https://auth.example.com",
            "api_gate_server_url": "https://api-gate.example.com",
            "agent_address": "https://agent.example.com",
        }

        with patch(
            "vitrina.uapi.views.template_views.OAuthClientManagement.create_oauth_client",
            return_value=(mocked_id, "some-secret"),
        ) as mock_create_oauth_client:
            response = app.post(url, data)

        assert response.status_code == HTTPStatus.FOUND
        assert AgentEnvironment.objects.filter(agent=agent).count() == 1
        assert mock_create_oauth_client.called

        agent_environment = AgentEnvironment.objects.filter(agent=agent).first()

        assert agent_environment.oauth_client_id == mocked_id
        assert agent_environment.auth_server_url == data["auth_server_url"]
        assert agent_environment.api_gate_server_url == data["api_gate_server_url"]
        assert agent_environment.agent_address == data["agent_address"]
        assert agent_environment.is_enabled is data["is_enabled"]
        assert agent_environment.environment == data["environment"]
        assert agent_environment.is_open_data_published
        assert agent_environment.open_data_publish_url == data["open_data_publish_url"]
        assert not agent_environment.is_archived
        assert agent_environment.is_enabled

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
        agent: Agent,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(reverse("agent-env-create", args=[organization.pk, agent.pk]), expect_errors=True)

        assert response.status_code == expected_status

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization, agent: Agent):
        breadcrumb_url_names_expected = [
            "home",
            "organization-list",
            "organization-detail",
            "agent-list",
            "agent-detail",
        ]

        url = reverse("agent-env-create", args=[organization.pk, agent.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected


class TestAgentEnvUpdate:
    def test_success(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent_environment: AgentEnvironment,
    ):
        app.set_user(representative_user)

        url = reverse("agent-env-update", args=[organization.pk, agent_environment.pk])
        data = {
            "is_enabled": False,
            "environment": Environment.PRODUCTION,
            "is_open_data_published": False,
            "open_data_publish_url": "https://data2.gov.lt",
            "auth_server_url": "https://auth2.example.com",
            "api_gate_server_url": "https://api-gate2.example.com",
            "agent_address": "https://agent2.example.com",
        }

        response = app.post(url, data)

        assert response.status_code == HTTPStatus.FOUND
        agent_environment.refresh_from_db()

        assert agent_environment.auth_server_url == data["auth_server_url"]
        assert agent_environment.api_gate_server_url == data["api_gate_server_url"]
        assert agent_environment.agent_address == data["agent_address"]
        assert agent_environment.is_enabled is data["is_enabled"]
        assert agent_environment.environment == data["environment"]
        assert not agent_environment.is_open_data_published
        assert agent_environment.open_data_publish_url == data["open_data_publish_url"]
        assert not agent_environment.is_enabled

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
        agent_environment: AgentEnvironment,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(
            reverse("agent-env-update", args=[organization.pk, agent_environment.pk]), expect_errors=True
        )

        assert response.status_code == expected_status

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization, agent_environment: AgentEnvironment):
        breadcrumb_url_names_expected = [
            "home",
            "organization-list",
            "organization-detail",
            "agent-list",
            "agent-detail",
            "agent-env-detail",
        ]

        url = reverse("agent-env-update", args=[organization.pk, agent_environment.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected


class TestAgentEnvDelete:
    def test_success(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent_environment: AgentEnvironment,
    ):
        app.set_user(representative_user)
        url = reverse("agent-env-delete", args=[organization.pk, agent_environment.pk])

        assert not agent_environment.is_archived

        response = app.post(url)

        assert response.status_code == HTTPStatus.FOUND
        assert AgentEnvironment.objects.count() == 1
        agent_environment = AgentEnvironment.objects.first()
        assert agent_environment.is_archived is True

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
        agent_environment: AgentEnvironment,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(
            reverse("agent-env-delete", args=[organization.pk, agent_environment.pk]), expect_errors=True
        )

        assert response.status_code == expected_status

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization, agent_environment: AgentEnvironment):
        breadcrumb_url_names_expected = [
            "home",
            "organization-list",
            "organization-detail",
            "agent-list",
            "agent-detail",
            "agent-env-detail",
        ]

        url = reverse("agent-env-delete", args=[organization.pk, agent_environment.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected


class TestAgentEnvDetail:
    def test_sucess(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent_environment: AgentEnvironment,
    ):
        app.set_user(representative_user)
        url = reverse("agent-env-detail", args=[organization.pk, agent_environment.pk])

        response = app.get(url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["agent_environment"] == agent_environment
        assert not response.context["secret"]

    @pytest.mark.parametrize("is_archived_agent", [True, False])
    def test_archived_agent(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        is_archived_agent: bool,
    ):
        app.set_user(representative_user)

        agent = AgentFactory(is_archived=is_archived_agent, organization=organization)
        agent_environment = AgentEnvironmentFactory(agent=agent, is_archived=not is_archived_agent)

        url = reverse("agent-env-detail", args=[organization.pk, agent_environment.pk])
        response = app.get(url, expect_errors=True)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_agent_env_detail_view_request_history(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent_environment: AgentEnvironment,
        request_history: RequestHistory,
    ):
        app.set_user(representative_user)
        url = reverse("agent-env-detail", args=[organization.pk, agent_environment.pk])

        response = app.get(url)

        assert response.status_code == HTTPStatus.OK
        assert list(response.context["agent_environment"].requesthistory.all()) == [request_history]
        assert response.context["agent_environment"] == agent_environment
        assert not response.context["secret"]

    def test_wrong_agent_detail_view_request_history_(
        self,
        app: DjangoTestApp,
        representative_user: User,
        organization: Organization,
        agent: Agent,
        request_history: RequestHistory,
    ):
        """Request_history is created for an agent which is not the one making the request."""

        another_agent_env = AgentEnvironmentFactory()
        app.set_user(representative_user)
        url = reverse("agent-env-detail", args=[another_agent_env.agent.organization.pk, another_agent_env.pk])

        response = app.get(url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["agent_environment"] == another_agent_env
        assert not response.context["secret"]
        assert list(response.context["agent_environment"].requesthistory.all()) == []

    @pytest.mark.parametrize(
        "user_fixture_name, expected_status",
        [
            (None, HTTPStatus.FOUND),
            ("user", HTTPStatus.FORBIDDEN),
            ("manager", HTTPStatus.FORBIDDEN),
            ("coordinator", HTTPStatus.OK),
            ("admin", HTTPStatus.OK),
        ],
    )
    def test_access_permissions(
        self,
        app: DjangoTestApp,
        organization: Organization,
        user_fixture_name: str | None,
        expected_status: int,
        request: FixtureRequest,
        agent_environment: AgentEnvironment,
    ):
        if user_fixture_name:
            app.set_user(request.getfixturevalue(user_fixture_name))

        response = app.get(
            reverse("agent-env-detail", args=[organization.pk, agent_environment.pk]), expect_errors=True
        )

        assert response.status_code == expected_status

    def test_breadcrumbs(self, app: DjangoTestApp, organization: Organization, agent_environment: AgentEnvironment):
        breadcrumb_url_names_expected = [
            "home",
            "organization-list",
            "organization-detail",
            "agent-list",
            "agent-detail",
        ]

        url = reverse("agent-env-detail", args=[organization.pk, agent_environment.pk])
        user = UserFactory(is_staff=True)
        app.set_user(user)
        response = app.get(url)

        breadcrumbs = response.context["parent_links"]
        breadcrumb_url_names_actual = [resolve(path).url_name for path in breadcrumbs if path]
        assert breadcrumb_url_names_actual == breadcrumb_url_names_expected
