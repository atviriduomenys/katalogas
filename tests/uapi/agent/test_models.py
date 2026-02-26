import pytest
from django.db import IntegrityError

from vitrina.orgs.factories import OrganizationFactory
from vitrina.uapi.models import Agent
from vitrina.uapi.factories import AgentFactory


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
