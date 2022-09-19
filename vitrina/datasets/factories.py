import factory
from factory.django import DjangoModelFactory

from vitrina.datasets.models import Dataset, DatasetStructure


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    slug = factory.Faker('word')
    is_public = True
    version = 1
    will_be_financed = False


class DatasetStructureFactory(DjangoModelFactory):
    class Meta:
        model = DatasetStructure
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    file = factory.django.FileField(filename='file.csv', data=b'Column\nValue')
    version = 1
