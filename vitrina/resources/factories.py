from datetime import date, datetime
from typing import Union

import factory
from django.utils.timezone import make_aware
from factory.django import DjangoModelFactory

from vitrina.classifiers.models import Concept
from vitrina.cms.factories import FilerFileFactory
from vitrina.datasets.factories import DatasetFactory
from vitrina.resources.models import (
    DatasetDistribution,
    Format,
    GeoportalFormat,
    GeoportalFormatValue,
    CompressionFormat,
    PackagingFormat,
    MediaType,
)


class FileFormat(DjangoModelFactory):
    class Meta:
        model = Format
        django_get_or_create = ("title", "extension")

    title = factory.Faker("word")
    extension = "CSV"


class UapiFormat(DjangoModelFactory):
    class Meta:
        model = Format
        django_get_or_create = ("title", "extension")

    title = "Saugykla API"
    extension = "UAPI"


class DatasetDistributionFactory(DjangoModelFactory):
    class Meta:
        model = DatasetDistribution
        django_get_or_create = ("title", "description")

    title = factory.Dict(
        {
            "en": factory.Faker("text", max_nb_chars=20, locale="en_US"),
            "lt": factory.Faker("text", max_nb_chars=20, locale="lt_LT"),
        }
    )
    description = factory.Dict(
        {
            "en": factory.Faker("text", locale="en_US"),
            "lt": factory.Faker("text", locale="lt_LT"),
        }
    )
    conditions = factory.Dict(
        {
            "en": factory.Faker("text", locale="en_US"),
            "lt": factory.Faker("text", locale="lt_LT"),
        }
    )
    dataset = factory.SubFactory(DatasetFactory)
    format = factory.SubFactory(FileFormat)
    period_start = date(2022, 1, 1)
    period_end = date(2022, 12, 31)
    file = factory.SubFactory(FilerFileFactory)
    type = "FILE"
    version = 1
    status = factory.LazyFunction(
        lambda: Concept.objects.get_or_create(
            code="DEVELOP",
            defaults={
                "valid_since": make_aware(datetime(2020, 1, 1)),
                "label": "Develop",
            },
        )[0]
    )
    name = factory.Sequence(lambda n: f"resource{n + 1}")

    class Params:
        uapi_format = factory.Trait(
            format=factory.SubFactory(UapiFormat),
            type="URL",
        )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        title = kwargs.pop("title")
        description = kwargs.pop("description")
        conditions = kwargs.pop("conditions")
        dataset = model_class(*args, **kwargs)
        for lang in ("en", "lt"):
            dataset.set_current_language(lang)
            dataset.title = _get_language_value(lang, title)
            dataset.description = _get_language_value(lang, description)
            dataset.conditions = _get_language_value(lang, conditions)
        dataset.save()
        return dataset


def _get_language_value(lang: str, value: Union[str | dict]) -> str:
    if isinstance(value, str):
        return value
    else:
        return value[lang]


class GeoportalFormatFactory(DjangoModelFactory):
    class Meta:
        model = GeoportalFormat

    format = factory.SubFactory(FileFormat)


class GeoportalFormatValueFactory(DjangoModelFactory):
    class Meta:
        model = GeoportalFormatValue

    geoportal_format = factory.SubFactory(GeoportalFormatFactory)
    value = factory.Faker("word")


class CompressionFormatFactory(DjangoModelFactory):
    class Meta:
        model = CompressionFormat

    title = factory.Faker("word")
    extension = factory.Faker("word")


class PackagingFormatFactory(DjangoModelFactory):
    class Meta:
        model = PackagingFormat

    title = factory.Faker("word")
    extension = factory.Faker("word")


class MediaTypeFactory(DjangoModelFactory):
    class Meta:
        model = MediaType

    title = factory.Faker("word")
    uri = factory.Faker("url")
