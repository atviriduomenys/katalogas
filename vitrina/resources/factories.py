import factory
from factory.django import DjangoModelFactory

from vitrina.resources.models import DatasetDistribution


class DatasetDistributionFactory(DjangoModelFactory):
    class Meta:
        model = DatasetDistribution
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    filename = factory.django.FileField(filename='file.csv', data=b'Column\nValue')
    version = 1
