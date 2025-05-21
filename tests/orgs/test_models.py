import pytest

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
