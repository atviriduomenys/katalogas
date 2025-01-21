from datetime import datetime, date
from typing import Union

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

class UapiFormat(DjangoModelFactory):
    class Meta:
        model = Format
        django_get_or_create = ('title', 'extension')

    title = 'Saugykla API'
    extension = 'UAPI'


class DatasetDistributionFactory(DjangoModelFactory):
    class Meta:
        model = DatasetDistribution
        django_get_or_create = ('title', 'description')

    title = factory.Dict({
        'en': factory.Faker('text', max_nb_chars=20, locale='en_US'),
        'lt': factory.Faker('text', max_nb_chars=20, locale='lt_LT'),
    })
    description = factory.Dict({
        'en': factory.Faker('text', locale='en_US'),
        'lt': factory.Faker('text', locale='lt_LT'),
    })
    dataset = factory.SubFactory(DatasetFactory)
    format = factory.SubFactory(FileFormat)
    period_start = date(2022, 1, 1)
    period_end = date(2022, 12, 31)
    file = factory.SubFactory(FilerFileFactory)
    type = "FILE"
    version = 1

    class Params:
        uapi_format = factory.Trait(
            format=factory.SubFactory(UapiFormat),
            type="URL",
        )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        title = kwargs.pop('title')
        description = kwargs.pop('description')
        dataset = model_class(*args, **kwargs)
        for lang in ('en', 'lt'):
            dataset.set_current_language(lang)
            dataset.title = _get_language_value(lang, title)
            dataset.description = _get_language_value(lang, description)
        dataset.save()
        return dataset


def _get_language_value(lang: str, value: Union[str | dict]) -> str:
    if isinstance(value, str):
        return value
    else:
        return value[lang]
