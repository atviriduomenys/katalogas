import factory
from factory.django import DjangoModelFactory

from vitrina.orgs.models import Organization, Representative
from vitrina.users.factories import UserFactory


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization
        django_get_or_create = ('title',)

    title = factory.Faker('company')
    kind = factory.Faker('word')
    version = 1

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.add_root(**kwargs)


class RepresentativeFactory(DjangoModelFactory):
    class Meta:
        model = Representative
        django_get_or_create = ('first_name', 'last_name', 'email', 'phone')

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    phone = factory.Sequence(lambda n: '+3706%07d' % n)
    version = 1
    role = Representative.COORDINATOR
    email = factory.LazyAttribute(lambda obj: f"{obj.first_name}.{obj.last_name}@gmail.com")
    user = factory.SubFactory(
        UserFactory,
        first_name=factory.SelfAttribute('..first_name'),
        last_name=factory.SelfAttribute('..last_name'),
        phone=factory.SelfAttribute('..phone'),
        email=factory.SelfAttribute('..email'),
    )

