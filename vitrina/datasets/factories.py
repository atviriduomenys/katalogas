import factory
from factory.django import DjangoModelFactory

from vitrina.orgs.factories import OrganizationFactory
from vitrina.datasets.models import Dataset, DatasetMember, DatasetStructure


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('title', 'slug', 'organization')

    organization = factory.SubFactory(OrganizationFactory)
    title = factory.Faker('catch_phrase')
    slug = factory.Faker('word')
    version = 1
    will_be_financed = False


class DatasetMemberFactory(DjangoModelFactory):
    class Meta:
        model = DatasetMember
        django_get_or_create = ('role', )

    role = DatasetMember.CREATOR
    contact = False


class DatasetStructureFactory(DjangoModelFactory):
    class Meta:
        model = DatasetStructure
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    file = factory.django.FileField(filename='file.csv', data=b'Column\nValue')
    version = 1
