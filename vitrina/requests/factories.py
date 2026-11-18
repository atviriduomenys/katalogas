import factory
import faker
from factory.django import DjangoModelFactory

from vitrina.datasets.factories import DatasetFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.requests.models import (
    Request,
    RequestStructure,
    RequestObject,
    RequestAssignment,
)


fake = faker.Faker()


class RequestFactory(DjangoModelFactory):
    class Meta:
        model = Request

    version = 1
    is_existing = True
    is_public = True
    dataset = factory.SubFactory(DatasetFactory)
    # Lithuanian title; translations__title_lt / translations__title_en override it.
    title = factory.Faker("catch_phrase")

    @factory.post_generation
    def organizations(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for org in extracted:
                self.organizations.add(org)

    @factory.post_generation
    def translations(obj, create, extracted, **kwargs):
        if not create:
            return

        # Lithuanian
        default_title = obj.safe_translation_getter("title", any_language=True)
        obj.set_current_language("lt")
        obj.title = kwargs.get("title_lt", default_title)
        obj.description = kwargs.get("description_lt", fake.text())
        obj.save()

        # English
        obj.set_current_language("en")
        obj.title = kwargs.get("title_en", fake.catch_phrase())
        obj.description = kwargs.get("description_en", fake.text())
        obj.save()


class RequestStructureFactory(DjangoModelFactory):
    class Meta:
        model = RequestStructure
        django_get_or_create = (
            "data_title",
            "data_notes",
            "data_type",
            "dictionary_title",
        )

    version = 1
    data_title = factory.Faker("catch_phrase")
    data_notes = factory.Faker("catch_phrase")
    data_type = factory.Faker("catch_phrase")
    dictionary_title = factory.Faker("catch_phrase")


class RequestObjectFactory(DjangoModelFactory):
    class Meta:
        model = RequestObject

    request = factory.SubFactory(RequestFactory)


class RequestAssignmentFactory(DjangoModelFactory):
    class Meta:
        model = RequestAssignment

    organization = factory.SubFactory(OrganizationFactory)
    request = factory.SubFactory(RequestFactory)
