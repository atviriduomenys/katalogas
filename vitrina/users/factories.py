import factory
from factory.django import DjangoModelFactory

from vitrina.users.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('first_name', 'last_name', 'email', 'phone')

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.LazyAttributeSequence(lambda o, n: '%s.%s%d@example.com' % (o.first_name, o.last_name, n))
    phone = factory.Sequence(lambda n: '+3706%07d' % n)
    version = 1


class ManagerFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('first_name', 'last_name', 'email', 'phone',)

    first_name = factory.Faker('last_name')
    last_name = factory.Faker('last_name')
    email = factory.LazyAttributeSequence(lambda o, n: '%s.%s%d@example.com' % (o.first_name, o.last_name, n))
    phone = factory.Sequence(lambda n: '+3706%07d' % n)
    organization = factory.SubFactory('vitrina.orgs.factories.OrganizationFactory')
