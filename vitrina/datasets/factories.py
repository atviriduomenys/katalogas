import factory
from django.apps import apps
from factory.django import DjangoModelFactory

from vitrina import settings
from vitrina.orgs.factories import OrganizationFactory
from vitrina.datasets.models import Dataset, DatasetStructure


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('organization', 'is_public')

    organization = factory.SubFactory(OrganizationFactory)
    is_public = True
    version = 1
    will_be_financed = False
    status = Dataset.HAS_DATA


class DatasetTranslationFactory(DjangoModelFactory):
    class Meta:
        model = apps.get_model('vitrina_datasets', 'DatasetTranslation')
        django_get_or_create = ('master', 'title', 'description', 'language_code')

    master = factory.SubFactory(DatasetFactory)
    language_code = 'en'
    title = factory.Faker('catch_phrase')
    description = factory.Faker('catch_phrase')


class DatasetStructureFactory(DjangoModelFactory):
    class Meta:
        model = DatasetStructure
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    file = factory.django.FileField(filename='file.csv', data=b'Column\nValue')
    version = 1
