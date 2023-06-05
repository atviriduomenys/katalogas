import factory
import uuid

from factory.django import DjangoModelFactory

from vitrina.datasets.factories import DatasetFactory
from vitrina.structure.models import Model, Metadata, Property


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
