import pytest
from django.db import IntegrityError

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.orgs.models import Agent


@pytest.mark.django_db
def test_codename_set_automatically_for_newly_created_agent():
    organization = OrganizationFactory()
    dataset = DatasetFactory()
    agent = Agent.objects.create(
        title="abc def 123",
        organization=organization,
        service=dataset
    )

    assert agent.codename == "abc_def_123"


@pytest.mark.django_db
def test_unique_name_and_organization_for_not_archived_agents_constraint():
    organization = OrganizationFactory()
    dataset = DatasetFactory()

    Agent.objects.create(title="agent", organization=organization, service=dataset)

    with pytest.raises(IntegrityError):
        Agent.objects.create(title="agent", organization=organization, service=dataset)


@pytest.mark.django_db
def test_unique_name_and_organization_for_archived_agents_constraint_name_duplicated_one_object_archived():
    """The uniqueness check should allow creating an object with a repeating code name, if the others are archived."""
    organization = OrganizationFactory()
    dataset = DatasetFactory()

    Agent.objects.create(title="agent", organization=organization, service=dataset, is_archived=True)
    Agent.objects.create(title="agent", organization=organization, service=dataset)
