import factory
from factory.django import DjangoModelFactory

from vitrina.uapi.models import Agent, AgentEnvironment, RequestHistory
from vitrina.uapi import Environment
from vitrina.orgs.factories import OrganizationFactory


class AgentFactory(DjangoModelFactory):
    class Meta:
        model = Agent
        django_get_or_create = ("organization", "title")

    # Unique, so get_or_create never returns an agent created earlier with the same random word.
    title = factory.Sequence(lambda n: f"agent-{n}")
    organization = factory.SubFactory(OrganizationFactory)


class AgentEnvironmentFactory(DjangoModelFactory):
    class Meta:
        model = AgentEnvironment
        django_get_or_create = ("agent", "environment")

    agent = factory.SubFactory(AgentFactory)
    environment = Environment.DEVELOPMENT
    is_enabled = True


class RequestHistoryFactory(DjangoModelFactory):
    class Meta:
        model = RequestHistory

    agent_environment = factory.SubFactory(AgentEnvironmentFactory)
    http_result = factory.Faker("random_int")
