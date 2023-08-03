import factory
import uuid

from factory.django import DjangoModelFactory

from vitrina.datasets.factories import DatasetFactory
from vitrina.structure.models import Model, Metadata, Property, Prefix, Enum, EnumItem, Param, ParamItem


class MetadataFactory(DjangoModelFactory):
    class Meta:
        model = Metadata

    uuid = str(uuid.uuid4())
    dataset = factory.SubFactory(DatasetFactory)
    name = factory.Faker('word')
    title = factory.Faker('catch_phrase')
    description = factory.Faker('catch_phrase')
    version = 1
    access = Metadata.OPEN

    type = ''
    ref = ''
    source = ''
    prepare = ''
    prepare_ast = ''
    uri = ''


class ModelFactory(DjangoModelFactory):
    class Meta:
        model = Model

    dataset = factory.SubFactory(DatasetFactory)


class PropertyFactory(DjangoModelFactory):
    class Meta:
        model = Property

    model = factory.SubFactory(ModelFactory)


class EnumFactory(DjangoModelFactory):
    class Meta:
        model = Enum

    name = factory.Faker('word')


class EnumItemFactory(DjangoModelFactory):
    class Meta:
        model = EnumItem

    enum = factory.SubFactory(EnumFactory)


class PrefixFactory(DjangoModelFactory):
    class Meta:
        model = Prefix

    name = factory.Faker('word')


class ParamFactory(DjangoModelFactory):
    class Meta:
        model = Param

    name = factory.Faker('word')


class ParamItemFactory(DjangoModelFactory):
    class Meta:
        model = ParamItem

    param = factory.SubFactory(ParamFactory)
