from typing import Iterable

import factory
from factory.django import DjangoModelFactory

from vitrina.cms.factories import FilerImageFactory
from vitrina.datasets.models import Dataset
from vitrina.projects.models import Project, UseCaseClient, UseCaseClientScope


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project
        django_get_or_create = ("url",)

    url = factory.Faker("url")
    version = 1
    title = factory.Faker("catch_phrase")
    image = factory.SubFactory(FilerImageFactory)
    status = Project.APPROVED
    is_public = True

    @factory.post_generation
    def datasets(self, create: bool, extracted: Iterable[Dataset], **kwargs) -> None:
        if not create or not extracted:
            return

        self.datasets.add(*extracted)


class UseCaseClientFactory(DjangoModelFactory):
    class Meta:
        model = UseCaseClient

    use_case = factory.SubFactory(ProjectFactory)
    name = factory.Faker("catch_phrase")
    client_id = factory.Faker("uuid4")


class UseCaseClientScopeFactory(DjangoModelFactory):
    class Meta:
        model = UseCaseClientScope

    resource = factory.Faker("uri")
    action = "getall"
    scope = factory.Faker("uri")
    use_case_client = factory.SubFactory(UseCaseClientFactory)
    is_active = True
