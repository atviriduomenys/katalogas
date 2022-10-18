import factory
import faker
from factory.django import DjangoModelFactory

from vitrina import settings
from vitrina.orgs.factories import OrganizationFactory
from vitrina.datasets.models import Dataset, DatasetStructure


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('organization', 'is_public')

    organization = factory.SubFactory(OrganizationFactory)
    is_public = True
    version = 1
    will_be_financed = False
    status = Dataset.HAS_DATA

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        dataset = model_class(*args, **kwargs)
        fake = faker.Faker()
        for lang in reversed(settings.LANGUAGES):
            dataset.set_current_language(lang[0])
            dataset.title = fake.word
            dataset.description = fake.catch_phrase
        dataset.save()
        return dataset

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class DatasetStructureFactory(DjangoModelFactory):
    class Meta:
        model = DatasetStructure
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    file = factory.django.FileField(filename='file.csv', data=b'Column\nValue')
    version = 1
