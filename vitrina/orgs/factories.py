import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

from vitrina.orgs.models import Organization, Representative
from vitrina.users.factories import UserFactory


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization
        django_get_or_create = ('title', 'kind', 'name', 'company_code',
                                'email', 'phone', 'address')

    title = factory.Faker('company')
    kind = factory.Faker('word')
    name = factory.Sequence(lambda n: f'{Faker().last_name()}_{n:04d}'.lower())
    company_code = factory.Faker('bothify', text='?????????', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    email = factory.Faker('email')
    phone = Faker().phone_number()
    address = Faker().address()
    is_public = True
    version = 1

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        if not kwargs.get('created'):
            kwargs['created'] = timezone.now()
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
