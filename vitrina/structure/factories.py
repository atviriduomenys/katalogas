import factory
import uuid
from factory.django import DjangoModelFactory

from vitrina.datasets.factories import DatasetFactory
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
)

_shared_version = None

def get_shared_version():
    global _shared_version
    if _shared_version is None:
        _shared_version = VersionFactory()
    return _shared_version


class VersionFactory(DjangoModelFactory):
    class Meta:
        model = Version

    dataset = factory.SubFactory(DatasetFactory)
    status = VersionStatus.DRAFT

class MetadataFactory(DjangoModelFactory):
    class Meta:
        model = Metadata

    uuid = str(uuid.uuid4())
    dataset = factory.SelfAttribute("metadata_version.dataset")
    name = factory.Faker("word")
    title = factory.Faker("catch_phrase")
    description = factory.Faker("catch_phrase")
    version = 1
    access = Metadata.OPEN
    visibility = Metadata.UNDEFINED

    metadata_version = factory.LazyFunction(get_shared_version)
    type = ""
    ref = ""
    source = ""
    prepare = ""
    prepare_ast = ""
    uri = ""


class ModelFactory(DjangoModelFactory):
    class Meta:
        model = Model

    version = factory.LazyFunction(get_shared_version)
    dataset = factory.SelfAttribute("version.dataset")


class BaseFactory(DjangoModelFactory):
    class Meta:
        model = Base

    model = factory.SubFactory(ModelFactory)
    version = factory.SelfAttribute("model.version")


class PropertyFactory(DjangoModelFactory):
    class Meta:
        model = Property

    model = factory.SubFactory(ModelFactory)
    version = factory.SelfAttribute("model.version")


class EnumFactory(DjangoModelFactory):
    class Meta:
        model = Enum

    name = factory.Faker("word")
    version = factory.LazyFunction(get_shared_version)


class EnumItemFactory(DjangoModelFactory):
    class Meta:
        model = EnumItem

    enum = factory.SubFactory(EnumFactory)
    version = factory.SelfAttribute("enum.version")


class PrefixFactory(DjangoModelFactory):
    class Meta:
        model = Prefix

    name = factory.Faker("word")
    version = factory.LazyFunction(get_shared_version)


class ParamFactory(DjangoModelFactory):
    class Meta:
        model = Param

    name = factory.Faker("word")
    version = factory.LazyFunction(get_shared_version)


class ParamItemFactory(DjangoModelFactory):
    class Meta:
        model = ParamItem

    param = factory.SubFactory(ParamFactory)
    version = factory.SelfAttribute("param.version")
