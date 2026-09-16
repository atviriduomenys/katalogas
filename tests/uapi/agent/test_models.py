import json
import uuid

import pytest
import reversion
from reversion.models import Version
from django.db import IntegrityError

from vitrina.orgs.factories import OrganizationFactory
from vitrina.uapi.models import Agent, AgentEnvironment, RequestHistory
from vitrina.uapi.factories import AgentFactory, AgentEnvironmentFactory, RequestHistoryFactory
from vitrina.uapi.utils.utils import AGENT_INSTANCE_URI_PREFIX
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

    def test_not_archived_queryset(self):
        agent_not_archived = AgentFactory(is_archived=False)
        AgentFactory(is_archived=True)

        assert Agent.objects.count() == 2
        assert Agent.objects.not_archived().count() == 1
        assert Agent.objects.not_archived().first() == agent_not_archived

    def test_services_unassigned_when_archived(self):
        agent = AgentFactory()

        DatasetFactory(agent=agent)
        DatasetFactory(agent=agent)

        assert agent.services.count() == 2

        agent.is_archived = True
        agent.save()

        assert agent.services.count() == 0


class TestAgentEnvironment:
    def test_not_archived_queryset(self):
        agent = AgentFactory(is_archived=True)

        agent_env_not_archived = AgentEnvironmentFactory(is_archived=False)
        AgentEnvironmentFactory(is_archived=True)
        AgentEnvironmentFactory(is_archived=False, agent=agent)

        assert AgentEnvironment.objects.count() == 3
        assert AgentEnvironment.objects.not_archived().count() == 1
        assert AgentEnvironment.objects.not_archived().first() == agent_env_not_archived

    def test_instance_uri_generated_for_each_environment(self):
        agent_env_1 = AgentEnvironmentFactory()
        agent_env_2 = AgentEnvironmentFactory()

        for agent_env in (agent_env_1, agent_env_2):
            assert agent_env.instance_uri.startswith(AGENT_INSTANCE_URI_PREFIX)
            uuid.UUID(agent_env.instance_uri.removeprefix(AGENT_INSTANCE_URI_PREFIX))
        assert agent_env_1.instance_uri != agent_env_2.instance_uri

    def test_instance_uri_not_changed_on_save(self):
        agent_env = AgentEnvironmentFactory()
        instance_uri = agent_env.instance_uri

        agent_env.is_enabled = False
        agent_env.save()
        agent_env.refresh_from_db()

        assert agent_env.instance_uri == instance_uri

    def test_instance_uri_cannot_be_changed_on_save(self):
        agent_env = AgentEnvironmentFactory()
        instance_uri = agent_env.instance_uri

        agent_env.instance_uri = f"{AGENT_INSTANCE_URI_PREFIX}{uuid.uuid4()}"
        agent_env.save()
        agent_env.refresh_from_db()

        assert agent_env.instance_uri == instance_uri

    def test_instance_uri_kept_when_version_without_field_reverted(self):
        agent_env = AgentEnvironmentFactory(is_enabled=True)
        instance_uri = agent_env.instance_uri
        with reversion.create_revision():
            agent_env.save()
        version = Version.objects.get_for_object(agent_env).get()
        # A version saved before the 0008-0010 migrations has no `instance_uri`.
        serialized_data = json.loads(version.serialized_data)
        del serialized_data[0]["fields"]["instance_uri"]
        version.serialized_data = json.dumps(serialized_data)
        version.save(update_fields=["serialized_data"])
        AgentEnvironment.objects.filter(pk=agent_env.pk).update(is_enabled=False)

        Version.objects.get(pk=version.pk).revert()
        agent_env.refresh_from_db()

        assert agent_env.is_enabled
        assert agent_env.instance_uri == instance_uri

    def test_instance_uri_unique(self):
        agent_env = AgentEnvironmentFactory()

        with pytest.raises(IntegrityError):
            AgentEnvironmentFactory(instance_uri=agent_env.instance_uri)


class TestRequestHistory:
    def test_visible_queryset(self):
        agent_archived = AgentFactory(is_archived=True)
        agent_env_archived = AgentEnvironmentFactory(is_archived=True)
        agent_env_archived_agent = AgentEnvironmentFactory(is_archived=False, agent=agent_archived)

        request_history = RequestHistoryFactory()
        RequestHistoryFactory(agent_environment=agent_env_archived)
        RequestHistoryFactory(agent_environment=agent_env_archived_agent)

        assert RequestHistory.objects.count() == 3
        assert RequestHistory.objects.visible().count() == 1
        assert RequestHistory.objects.visible().first() == request_history
