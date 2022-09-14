import factory
from factory.django import DjangoModelFactory

from vitrina.orgs.models import Organization, Representative


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization
        django_get_or_create = ('title',)

    title = factory.Faker('company')
    slug = factory.Faker('word')
    kind = factory.Faker('word')
    version = 1

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.add_root(**kwargs)


class RepresentativeFactory(DjangoModelFactory):
    class Meta:
        model = Representative
        django_get_or_create = ('first_name', 'last_name',)

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    version = 1

