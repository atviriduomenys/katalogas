from typing import Union

import factory
import faker
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from factory.django import DjangoModelFactory, FileField

from vitrina import settings
from vitrina.classifiers.factories import FrequencyFactory, CategoryFactory
from vitrina.cms.factories import FilerFileFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.datasets.models import (
    Dataset,
    DatasetStructure,
    DatasetGroup,
    Type,
    Relation,
    DatasetRelation,
    Attribution,
    DatasetAttribution,
    Contact,
    DCATResourceSubclass,
    DatasetGroupCategoryUri,
)
from vitrina.structure.factories import MetadataFactory

MANIFEST = """\
id,dataset,resource,base,model,property,type,ref,source,prepare,level,status,visibility,access,uri,eli,title,description,count
,datasets/gov/ivpk/adk,,,,,,,,,,,,,,,Opend Data Portal,,
,,,,,,prefix,dcat,,,,,,,http://www.w3.org/ns/dcat#,,,,
,,,,,,,dct,,,,,,,http://purl.org/dc/terms/,,,,
,,,,,,,spinta,,,,,,,https://github.com/atviriduomenys/spinta/issues/,,,,
,,,,,,,,,,,,,,,,,
,,,,Dataset,,,id,,,5,,,,dcat:Dataset,,Dataset,,
,,,,,id,integer,,,,5,,,open,dct:identifier,,,,
,,,,,title,string,,,,2,,,open,dct:title,,,,
,,,,,,comment,type,,"update(property: ""title@lt"", type: ""text"")",4,,,open,spinta:204,,2022-10-23 11:00,,
,,,,,description,string,,,,2,,,open,dct:description,,,,
,,,,,,comment,type,,"update(property: ""description@lt"", type: ""text"")",4,,,open,spinta:204,,2022-10-23 11:00,,
,,,,,licence,ref,Licence,,,2,,,open,dct:license,,,,
,,,,,,,,,,,,,,,,,,
,,,,Licence,,,id,,,,,,,,,Licence,,
,,,,,id,integer,,,,5,,,open,dct:identifier,,Identifikatorius,,
,,,,,title,string,,,,2,,,open,dct:title,,,,
,,,,,,comment,type,,"update(property: ""title@lt"", type: ""text"")",4,,,open,spinta:204,,2022-10-23 11:00,,
"""


class DCATResourceSubclassFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DCATResourceSubclass

    name = "dataset"
    uri = ""

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        name = kwargs.get("name", "dataset")
        obj, created = model_class.objects.get_or_create(name=name, defaults=kwargs)
        return obj


class DatasetTranslationFactory(DjangoModelFactory):
    class Meta:
        model = Dataset.translations


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ("organization", "is_public")

    organization = factory.SubFactory(OrganizationFactory)
    uuid = factory.Faker("uuid4")
    is_public = True
    version = 1
    will_be_financed = False
    status = Dataset.HAS_DATA
    frequency = factory.SubFactory(FrequencyFactory)
    access_rights = Dataset.PUBLIC
    published = factory.Faker(
        "date_time",
        tzinfo=timezone.get_current_timezone(),
    )
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
    access_rights = Dataset.PUBLIC
    subclass = factory.SubFactory(DCATResourceSubclassFactory)

    @classmethod
    def _create(cls, model_class: type[Dataset], *args, **kwargs):
        title = kwargs.pop("title")
        description = kwargs.pop("description")
        dataset = model_class(*args, **kwargs)
        for lang in ("en", "lt"):
            dataset.set_current_language(lang)
            dataset.title = _get_language_value(lang, title)
            dataset.description = _get_language_value(lang, description)
        dataset = model_class.add_root(instance=dataset)
        return dataset

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)

    @factory.post_generation
    def category(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for category in extracted:
                self.category.add(category)

    @factory.post_generation
    def metadata(self, create: bool, extracted: str, **kwargs) -> None:
        if not create:
            return
        name = extracted if extracted is not None else "datasets/gov/ivpk/adp"
        MetadataFactory.create(
            dataset=self, content_type=ContentType.objects.get_for_model(self), object_id=self.pk, name=name
        )


def _get_language_value(lang: str, value: Union[str | dict]) -> str:
    if isinstance(value, str):
        return value
    else:
        return value[lang]


class AttributionFactory(DjangoModelFactory):
    class Meta:
        model = Attribution

    name = factory.Faker("word")
    title = factory.Faker("catch_phrase")


class DatasetAttributionFactory(DjangoModelFactory):
    class Meta:
        model = DatasetAttribution

    dataset = factory.SubFactory(DatasetFactory)
    attribution = factory.SubFactory(AttributionFactory)
    organization = factory.SubFactory(OrganizationFactory)


class DatasetStructureFactory(DjangoModelFactory):
    class Meta:
        model = DatasetStructure
        django_get_or_create = ("title",)

    version = 1
    title = factory.Faker("catch_phrase")
    file = factory.SubFactory(FilerFileFactory, file=FileField(filename="manifest.csv", data=MANIFEST))
    dataset = factory.SubFactory(DatasetFactory)


class DatasetGroupFactory(DjangoModelFactory):
    class Meta:
        model = DatasetGroup

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        group = model_class(*args, **kwargs)
        fake = faker.Faker()
        for lang in reversed(settings.LANGUAGES):
            group.set_current_language(lang[0])
            group.title = fake.uuid4()
        group.save()
        return group


class DatasetGroupCategoryUriFactory(DjangoModelFactory):
    class Meta:
        model = DatasetGroupCategoryUri

    group = factory.SubFactory(DatasetGroupFactory)
    category = factory.SubFactory(CategoryFactory)
    uri = factory.Faker("word")


class TypeFactory(DjangoModelFactory):
    class Meta:
        model = Type

    name = factory.Faker("word")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        type = model_class(*args, **kwargs)
        fake = faker.Faker()
        for lang in reversed(settings.LANGUAGES):
            type.set_current_language(lang[0])
            type.title = fake.uuid4()
        type.save()
        return type


class RelationFactory(DjangoModelFactory):
    class Meta:
        model = Relation

    name = factory.Faker("word")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        relation = model_class(*args, **kwargs)
        fake = faker.Faker()
        for lang in reversed(settings.LANGUAGES):
            relation.set_current_language(lang[0])
            relation.title = fake.uuid4()
            relation.inverse_title = fake.uuid4()
        relation.save()
        return relation


class DatasetRelationFactory(DjangoModelFactory):
    class Meta:
        model = DatasetRelation

    dataset = factory.SubFactory(DatasetFactory)
    part_of = factory.SubFactory(DatasetFactory)
    relation = factory.SubFactory(RelationFactory)


class ContactFactory(DjangoModelFactory):
    class Meta:
        model = Contact

    phone = factory.Faker("phone_number")
    email = factory.Faker("email")
    content_type = factory.LazyAttribute(lambda o: ContentType.objects.get_for_model(o.organization))
    object_id = factory.SelfAttribute("organization.id")
    organization = factory.SubFactory(OrganizationFactory)


class DatasetServiceFactory(DjangoModelFactory):
    class Meta:
        model = Dataset

    organization = factory.SubFactory(OrganizationFactory)
    uuid = factory.Faker("uuid4")
    is_public = True
    version = 1
    service = True
    title = factory.Dict(
        {
            "en": factory.Faker("text", max_nb_chars=20, locale="en_US"),
            "lt": factory.Faker("text", max_nb_chars=20, locale="lt_LT"),
        }
    )
    endpoint_url = factory.Faker("url")
    endpoint_description = factory.Faker("url")
    subclass = factory.SubFactory(DCATResourceSubclassFactory, name="service")
    contact = factory.SubFactory(ContactFactory, organization=factory.SelfAttribute("..organization"))

    @classmethod
    def _create(cls, model_class: type[Dataset], *args, **kwargs) -> Dataset:
        title = kwargs.pop("title")
        description = kwargs.pop("description", None)
        dataset = model_class(*args, **kwargs)
        for lang in ("en", "lt"):
            dataset.set_current_language(lang)
            dataset.title = _get_language_value(lang, title)
            dataset.description = _get_language_value(lang, description) if description else ""
        dataset = model_class.add_root(instance=dataset)
        return dataset

    @factory.post_generation
    def tags(self, create, extracted, **kwargs) -> None:
        if not create:
            return

        tag_names = extracted or ["test tag"]
        for tag_name in tag_names:
            self.tags.add(tag_name)

    @factory.post_generation
    def category(self, create, extracted, **kwargs) -> None:
        if not create:
            return
        if extracted:
            for category in extracted:
                self.category.add(category)

    @factory.post_generation
    def metadata(self, create: bool, extracted: str, **kwargs) -> None:
        if not create:
            return
        if extracted is False:
            return
        name = extracted if extracted is not None else ((self.organization.name or "test/dataset/") + "abcd")

        MetadataFactory.create(
            dataset=self, content_type=ContentType.objects.get_for_model(self), object_id=self.pk, name=name
        )
