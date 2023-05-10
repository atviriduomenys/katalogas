import factory
import faker
from factory.django import DjangoModelFactory

from vitrina.orgs.factories import OrganizationFactory
from vitrina.datasets.factories import DatasetFactory
from vitrina.requests.models import Request, RequestStructure


class RequestFactory(DjangoModelFactory):
    class Meta:
        model = Request
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    version = 1
    is_existing = True
    is_public = True
    organization = factory.SubFactory(OrganizationFactory)
    dataset = factory.SubFactory(DatasetFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        request = model_class(*args, **kwargs)
        fake = faker.Faker()
        request.title = fake.word()
        request.save()
        return request


class RequestStructureFactory(DjangoModelFactory):
    class Meta:
        model = RequestStructure
        django_get_or_create = ('data_title', 'data_notes', 'data_type', 'dictionary_title',)

    version = 1
    data_title = factory.Faker('catch_phrase')
    data_notes = factory.Faker('catch_phrase')
    data_type = factory.Faker('catch_phrase')
    dictionary_title = factory.Faker('catch_phrase')
