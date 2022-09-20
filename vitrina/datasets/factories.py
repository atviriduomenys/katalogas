import factory
from factory.django import DjangoModelFactory

from vitrina.datasets.models import Dataset, DatasetStructure
from vitrina.orgs.factories import OrganizationFactory


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('title', 'slug', 'organization')

    title = factory.Faker('catch_phrase')
    slug = factory.Faker('word')
    organization = factory.SubFactory(OrganizationFactory)
    version = 1
    will_be_financed = False


class DatasetStructureFactory(DjangoModelFactory):
    class Meta:
        model = DatasetStructure
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    file = factory.django.FileField(filename='file.csv', data=b'Column\nValue')
    version = 1
