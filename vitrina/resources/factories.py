from datetime import datetime, date

import factory
from factory.django import DjangoModelFactory

from vitrina.cms.factories import FilerFileFactory
from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.models import DatasetDistribution, Format


class FileFormat(DjangoModelFactory):
    class Meta:
        model = Format
        django_get_or_create = ('title', 'extension')

    title = factory.Faker('word')
    extension = 'CSV'


class DatasetDistributionFactory(DjangoModelFactory):
    class Meta:
        model = DatasetDistribution
        django_get_or_create = ('title', 'description')

    title = factory.Faker('catch_phrase')
    description = factory.Faker('catch_phrase')
    dataset = factory.SubFactory(DatasetFactory)
    format = factory.SubFactory(FileFormat)
    period_start = date(2022, 1, 1)
    period_end = date(2022, 12, 31)
    file = factory.SubFactory(FilerFileFactory)
    type = "FILE"
    version = 1
