from typing import Iterable

import factory
from factory.django import DjangoModelFactory

from vitrina.classifiers.models import (
    Activity,
    Category,
    FormFieldText,
    Frequency,
    Licence,
    AreaOfManagement,
    GeoportalCategory,
    GeoportalFrequency,
    ProvenanceStatement,
    Rule,
    Status,
    Concept,
    ConceptSchema,
    ApplicableLegislation,
)
from vitrina.datasets.models import Documentation


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


class StatusFactory(DjangoModelFactory):
    class Meta:
        model = Status
        django_get_or_create = ("codename",)

    codename = factory.Faker("word")


class ConceptSchemaFactory(DjangoModelFactory):
    class Meta:
        model = ConceptSchema


class ConceptFactory(DjangoModelFactory):
    class Meta:
        model = Concept
        django_get_or_create = ("code",)

    code = factory.Faker("word")
    valid_since = factory.Faker("date")

    @factory.post_generation
    def concept_schemas(self, create: bool, extracted: Iterable[ConceptSchema], **kwargs) -> None:
        if not create or not extracted:
            return None

        self.concept_schemas.add(*extracted)


class ApplicableLegislationFactory(DjangoModelFactory):
    class Meta:
        model = ApplicableLegislation
        django_get_or_create = ("url",)

    url = factory.Faker("url")
    description = factory.Faker("sentence")


class DocumentationFactory(DjangoModelFactory):
    class Meta:
        model = Documentation
        django_get_or_create = ("documentation_link",)

    documentation_link = factory.Faker("url")


class RuleFactory(DjangoModelFactory):
    class Meta:
        model = Rule

    identifier = factory.Sequence(lambda n: f"rule-{n}")


class ProvenanceStatementFactory(DjangoModelFactory):
    class Meta:
        model = ProvenanceStatement

    url = factory.Faker("url")
    description = factory.Faker("sentence")


class ActivityFactory(DjangoModelFactory):
    class Meta:
        model = Activity

    title = factory.Faker("catch_phrase")


class FormFieldTextFactory(DjangoModelFactory):
    class Meta:
        model = FormFieldText

    form_name = FormFieldText.DCAT_DATASET
    field_name = factory.Faker("word")

    @classmethod
    def _create(cls, model_class: type[FormFieldText], *args, **kwargs) -> FormFieldText:
        help_text_lt = kwargs.pop("help_text_lt", "")
        help_text_en = kwargs.pop("help_text_en", "")
        label_lt = kwargs.pop("label_lt", "")
        label_en = kwargs.pop("label_en", "")
        entry = model_class(*args, **kwargs)
        entry.set_current_language("lt")
        entry.help_text = help_text_lt
        entry.label = label_lt
        entry.set_current_language("en")
        entry.help_text = help_text_en
        entry.label = label_en
        entry.save()
        return entry
