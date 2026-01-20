import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from vitrina.datasets.factories import DatasetFactory, AgentFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.uapi.models import Agent


pytestmark = pytest.mark.django_db


class TestAgent:
    def test_codename_set_automatically_for_newly_created_agent(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(service=True)
        agent = Agent.objects.create(
            title="abc def 123",
            organization=organization,
            service=dataset
        )

        assert agent.codename == "abc_def_123"


    def test_unique_name_and_organization_for_not_archived_agents_constraint(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(service=True)

        Agent.objects.create(title="agent", organization=organization, service=dataset)

        with pytest.raises(IntegrityError):
            Agent.objects.create(title="agent", organization=organization, service=dataset)


    def test_unique_name_and_organization_for_archived_agents_constraint_name_duplicated_one_object_archived(self):
        """The uniqueness check should allow creating an object with a repeating code name if others are archived."""
        organization = OrganizationFactory()
        dataset = DatasetFactory(service=True)

        Agent.objects.create(title="agent", organization=organization, service=dataset, is_archived=True)
        Agent.objects.create(title="agent", organization=organization, service=dataset)


    def test_agent_created_with_attached_data_resource_that_is_not_service(self):
        organization = OrganizationFactory()
        dataset = DatasetFactory(service=False)

        with pytest.raises(ValidationError):
            Agent.objects.create(title="agent", organization=organization, service=dataset)


    def test_update_agent_codename_when_agent_title_updated_using_update_fields(self) -> None:
        agent = AgentFactory()
        agent.title = "foo"
        agent.save(update_fields=["title"])

        agent.refresh_from_db()
        assert agent.codename == "foo"
