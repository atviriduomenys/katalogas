import factory
from factory.django import DjangoModelFactory

from vitrina.classifiers.models import (
    Category,
    Frequency,
    Licence,
    AreaOfManagement,
    GeoportalCategory,
    GeoportalFrequency,
    GeoportalLicence,
    GeoportalAccessRights,
)


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("title",)

    title = factory.Faker("catch_phrase")
    description = factory.Faker("catch_phrase")
    version = 1
    featured = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.add_root(**kwargs)


class FrequencyFactory(DjangoModelFactory):
    class Meta:
        model = Frequency
        django_get_or_create = ("title",)

    title = factory.Faker("word")


class LicenceFactory(DjangoModelFactory):
    class Meta:
        model = Licence
        django_get_or_create = ("title",)

    identifier = factory.Sequence(lambda n: f"id{n}")
    title = factory.Faker("word")
    description = factory.Faker("catch_phrase")


class AreaOfManagementFactory(DjangoModelFactory):
    class Meta:
        model = AreaOfManagement
        django_get_or_create = ("name_lt", "name_en")

    id = factory.Sequence(lambda n: n + 2)
    name_lt = factory.LazyAttribute(lambda obj: f"Jurisdiction{obj.id}")
    name_en = factory.LazyAttribute(lambda obj: f"Jurisdikcija{obj.id}")


class GeoportalCategoryFactory(DjangoModelFactory):
    class Meta:
        model = GeoportalCategory
        django_get_or_create = ("title",)

    title = factory.Faker("catch_phrase")


class GeoportalFrequencyFactory(DjangoModelFactory):
    class Meta:
        model = GeoportalFrequency
        django_get_or_create = ("title",)

    title = factory.Faker("catch_phrase")
    frequency = factory.SubFactory(FrequencyFactory)


class GeoportalLicenceFactory(DjangoModelFactory):
    class Meta:
        model = GeoportalLicence
        django_get_or_create = ("title",)

    title = factory.Faker("catch_phrase")
    licence = factory.SubFactory(LicenceFactory)


class GeoportalAccessRightsFactory(DjangoModelFactory):
    class Meta:
        model = GeoportalAccessRights
        django_get_or_create = ("title",)

    title = factory.Faker("catch_phrase")
    access_rights = GeoportalAccessRights.PUBLIC
