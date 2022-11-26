import factory
from factory.django import DjangoModelFactory

from vitrina.catalogs.models import Catalog
from vitrina.classifiers.factories import LicenceFactory


class CatalogFactory(DjangoModelFactory):
    class Meta:
        model = Catalog
        django_get_or_create = ('title', 'description',)

    identifier = factory.Faker('word')
    title = factory.Faker('catch_phrase')
    description = factory.Faker('catch_phrase')
    licence = factory.SubFactory(LicenceFactory)
    version = 1
