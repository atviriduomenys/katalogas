import factory
from factory.django import DjangoModelFactory

from vitrina.datasets.models import Dataset
from vitrina.orgs.factories import OrganizationFactory


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('title', 'slug', 'organization')

    organization = factory.SubFactory(OrganizationFactory)
    title = factory.Faker('catch_phrase')
    slug = factory.Faker('word')
    version = 1
    will_be_financed = False
