import factory
import uuid

from factory.django import DjangoModelFactory

from vitrina.structure import VersionStatus
from vitrina.structure.models import (
    Model,
    Metadata,
    Property,
    Prefix,
    Enum,
    EnumItem,
    Param,
    ParamItem,
    Base,
    Version,
    UMLDiagram,
)


class VersionFactory(DjangoModelFactory):
    class Meta:
        model = Version

    dataset = factory.SubFactory("vitrina.datasets.factories.DatasetFactory")
    status = VersionStatus.DRAFT
    version = factory.Sequence(lambda n: n + 1)


class MetadataFactory(DjangoModelFactory):
    class Meta:
        model = Metadata

    uuid = factory.LazyFunction(uuid.uuid4)
    dataset = factory.SubFactory("vitrina.datasets.factories.DatasetFactory")
    name = factory.Faker("word")
    title = factory.Faker("catch_phrase")
    description = factory.Faker("catch_phrase")
    version = 1
    access = Metadata.OPEN
    visibility = Metadata.UNDEFINED

    metadata_version = factory.SubFactory(VersionFactory, dataset=factory.SelfAttribute("..dataset"))
    type = ""
    ref = ""
    source = ""
    prepare = ""
    prepare_ast = ""
    uri = ""


class ModelFactory(DjangoModelFactory):
    class Meta:
        model = Model

    metadata_version = factory.SubFactory(VersionFactory)
    dataset = factory.SelfAttribute("metadata_version.dataset")


class BaseFactory(DjangoModelFactory):
    class Meta:
        model = Base

    model = factory.SubFactory(ModelFactory)
    metadata_version = factory.SelfAttribute("model.metadata_version")


class PropertyFactory(DjangoModelFactory):
    class Meta:
        model = Property

    model = factory.SubFactory(ModelFactory)
    metadata_version = factory.SelfAttribute("model.metadata_version")


class EnumFactory(DjangoModelFactory):
    class Meta:
        model = Enum

    name = factory.Faker("word")
    metadata_version = factory.SubFactory(VersionFactory)


class EnumItemFactory(DjangoModelFactory):
    class Meta:
        model = EnumItem

    enum = factory.SubFactory(EnumFactory)
    metadata_version = factory.SelfAttribute("enum.metadata_version")


class PrefixFactory(DjangoModelFactory):
    class Meta:
        model = Prefix

    name = factory.Faker("word")
    metadata_version = factory.SubFactory(VersionFactory)


class ParamFactory(DjangoModelFactory):
    class Meta:
        model = Param

    name = factory.Faker("word")
    metadata_version = factory.SubFactory(VersionFactory)


class ParamItemFactory(DjangoModelFactory):
    class Meta:
        model = ParamItem

    param = factory.SubFactory(ParamFactory)
    metadata_version = factory.SelfAttribute("param.metadata_version")


class UMLDiagramFactory(DjangoModelFactory):
    class Meta:
        model = UMLDiagram

    metadata_version = factory.SubFactory(VersionFactory)
