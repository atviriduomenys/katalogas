from factory import SubFactory
from factory.django import DjangoModelFactory

from vitrina.datasets.factories import DatasetFactory
from vitrina.uapi.models import Agent


class AgentFactory(DjangoModelFactory):
    class Meta:
        model = Agent
        django_get_or_create = ("organization", "service")

    service = SubFactory(DatasetFactory, service=True)
