import pytest
from django.db import IntegrityError

from vitrina.orgs.factories import OrganizationFactory
from vitrina.uapi.models import Agent, AgentEnvironment, RequestHistory
from vitrina.uapi.factories import AgentFactory, AgentEnvFactory, RequestHistoryFactory
from vitrina.datasets.factories import DatasetFactory


pytestmark = pytest.mark.django_db


class TestAgent:
    def test_codename_set_automatically_for_newly_created_agent(self):
        organization = OrganizationFactory()
        agent = Agent.objects.create(title="abc def 123", organization=organization)

        assert agent.codename == "abc_def_123"

    def test_unique_name_and_organization_for_not_archived_agents_constraint(self):
        organization = OrganizationFactory()

        Agent.objects.create(title="agent", organization=organization)

        with pytest.raises(IntegrityError):
            Agent.objects.create(title="agent", organization=organization)

    def test_unique_name_and_organization_for_archived_agents_constraint_name_duplicated_one_object_archived(self):
        """The uniqueness check should allow creating an object with a repeating code name if others are archived."""
        organization = OrganizationFactory()

        Agent.objects.create(title="agent", organization=organization, is_archived=True)
        Agent.objects.create(title="agent", organization=organization)

    def test_update_agent_codename_when_agent_title_updated_using_update_fields(self) -> None:
        agent = AgentFactory()
        agent.title = "foo"
        agent.save(update_fields=["title"])

        agent.refresh_from_db()
        assert agent.codename == "foo"

    def test_not_archived_manager(self):
        agent_not_archived = AgentFactory(is_archived=False)
        AgentFactory(is_archived=True)

        assert Agent.objects.count() == 2
        assert Agent.not_archived.count() == 1
        assert Agent.not_archived.first() == agent_not_archived

    def test_services_unassigned_when_archived(self):
        agent = AgentFactory()

        DatasetFactory(agent=agent)
        DatasetFactory(agent=agent)

        assert agent.services.count() == 2

        agent.is_archived = True
        agent.save()

        assert agent.services.count() == 0


class TestAgentEnvironment:
    def test_not_archived_manager(self):
        agent = AgentFactory(is_archived=True)

        agent_env_not_archived = AgentEnvFactory(is_archived=False)
        AgentEnvFactory(is_archived=True)
        AgentEnvFactory(is_archived=False, agent=agent)

        assert AgentEnvironment.objects.count() == 3
        assert AgentEnvironment.not_archived.count() == 1
        assert AgentEnvironment.not_archived.first() == agent_env_not_archived


class TestRequestHistory:
    def test_visible_manager(self):
        agent_archived = AgentFactory(is_archived=True)
        agent_env_archived = AgentEnvFactory(is_archived=True)
        agent_env_archived_agent = AgentEnvFactory(is_archived=False, agent=agent_archived)

        request_history = RequestHistoryFactory()
        RequestHistoryFactory(agent_environment=agent_env_archived)
        RequestHistoryFactory(agent_environment=agent_env_archived_agent)

        assert RequestHistory.objects.count() == 3
        assert RequestHistory.visible.count() == 1
        assert RequestHistory.visible.first() == request_history
