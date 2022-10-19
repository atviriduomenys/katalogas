import factory
from factory.django import DjangoModelFactory

from vitrina.classifiers.models import Category, Frequency, Licence


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    version = 1
    featured = False


class FrequencyFactory(DjangoModelFactory):
    class Meta:
        model = Frequency
        django_get_or_create = ('title',)

    title = factory.Faker('word')


class LicenceFactory(DjangoModelFactory):
    class Meta:
        model = Licence
        django_get_or_create = ('title',)

    title = factory.Faker('word')
