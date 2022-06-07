import factory
from factory.django import DjangoModelFactory

from vitrina.orgs.models import Organization


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization
        django_get_or_create = ('title',)

    title = factory.Faker('company')
    version = 1
