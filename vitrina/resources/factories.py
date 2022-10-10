from datetime import datetime, date

import factory
from factory.django import DjangoModelFactory

from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.models import DatasetDistribution


class DatasetDistributionFactory(DjangoModelFactory):
    class Meta:
        model = DatasetDistribution
        django_get_or_create = ('title', 'description')

    title = factory.Faker('catch_phrase')
    description = factory.Faker('catch_phrase')
    dataset = factory.SubFactory(DatasetFactory)
    file = factory.django.FileField(filename='file.csv', data=b'Column\nValue')
    version = 1
