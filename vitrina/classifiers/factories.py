import factory
from factory.django import DjangoModelFactory

from vitrina.classifiers.models import Category, Frequency, Licence


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    description = factory.Faker('catch_phrase')
    version = 1
    featured = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        category = model_class(*args, **kwargs)
        fake = faker.Faker()
        for lang in reversed(settings.LANGUAGES):
            category.set_current_language(lang[0])
            category.title = fake.word()
        category.save()
        return category



class FrequencyFactory(DjangoModelFactory):
    class Meta:
        model = Frequency
        django_get_or_create = ('title',)

    title = factory.Faker('word')


class LicenceFactory(DjangoModelFactory):
    class Meta:
        model = Licence
        django_get_or_create = ('title',)

    identifier = factory.Sequence(lambda n: f'id{n}')
    title = factory.Faker('word')
    description = factory.Faker('catch_phrase')
