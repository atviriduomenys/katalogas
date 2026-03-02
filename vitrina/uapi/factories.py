import factory
from factory.django import DjangoModelFactory

from vitrina.uapi.models import Agent, AgentEnv, RequestHistory
from vitrina.uapi import Environment
from vitrina.orgs.factories import OrganizationFactory


class AgentFactory(DjangoModelFactory):
    class Meta:
        model = Agent
        django_get_or_create = ("organization", "title")

    title = factory.Faker("word")
    organization = factory.SubFactory(OrganizationFactory)


class AgentEnvFactory(DjangoModelFactory):
    class Meta:
        model = AgentEnv
        django_get_or_create = ("agent", "environment")

    agent = factory.SubFactory(AgentFactory)
    environment = Environment.DEVELOPMENT
    is_enabled = True


class RequestHistoryFactory(DjangoModelFactory):
    class Meta:
        model = RequestHistory

    agent_env = factory.SubFactory(AgentEnvFactory)
    http_result = factory.Faker("random_int")
