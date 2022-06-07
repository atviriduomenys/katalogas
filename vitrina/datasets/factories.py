import factory
from factory.django import DjangoModelFactory

from vitrina.datasets.models import Dataset


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    version = 1
    will_be_financed = False
