import factory
from django.apps import apps
from factory.django import DjangoModelFactory

from vitrina import settings
from vitrina.orgs.factories import OrganizationFactory
from vitrina.datasets.models import Dataset, DatasetStructure


class DatasetTranslationFactory(DjangoModelFactory):
    class Meta:
        model = apps.get_model('vitrina_datasets', 'DatasetTranslation')
        django_get_or_create = ('title', 'description')

    language_code = 'en'
    title = factory.Faker('catch_phrase')
    description = factory.Faker('catch_phrase')


class DatasetFactory(DjangoModelFactory):
    class Meta:
        model = Dataset
        django_get_or_create = ('title', 'description', 'organization', 'is_public')

    organization = factory.SubFactory(OrganizationFactory)
    title = factory.Faker('catch_phrase')
    description = factory.Faker('catch_phrase')
    is_public = True
    version = 1
    will_be_financed = False
    status = Dataset.HAS_DATA

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = super()._create(model_class, *args, **kwargs)
        obj.set_current_language('en')
        obj.save()
        translations = factory.SubFactory(DatasetTranslationFactory, master_id=obj.pk)
        obj.translations.set(translations)
        obj.save()
        return obj


class DatasetStructureFactory(DjangoModelFactory):
    class Meta:
        model = DatasetStructure
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    file = factory.django.FileField(filename='file.csv', data=b'Column\nValue')
    version = 1
