import factory
from factory.django import DjangoModelFactory

from vitrina.classifiers.factories import CategoryFactory, LicenceFactory, FrequencyFactory
from vitrina.orgs.factories import OrganizationFactory
from vitrina.datasets.models import Dataset, DatasetStructure


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('title', 'organization', 'is_public')

    organization = factory.SubFactory(OrganizationFactory)
    title = factory.Faker('catch_phrase')
    is_public = True
    version = 1
    will_be_financed = False
    status = Dataset.HAS_DATA
    category = factory.SubFactory(CategoryFactory)
    licence = factory.SubFactory(LicenceFactory)
    frequency = factory.SubFactory(FrequencyFactory)

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
