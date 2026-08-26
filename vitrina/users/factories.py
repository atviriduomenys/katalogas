import factory
from factory.django import DjangoModelFactory

from vitrina.users.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        # Keyed on email alone: it is unique in the database, so a second call
        # with an email that is already taken has to return that user. Keying
        # on the other fields too would miss on the lookup - they are random -
        # and then fail on the constraint.
        django_get_or_create = ("email",)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttributeSequence(lambda o, n: "%s.%s%d@example.com" % (o.first_name, o.last_name, n))
    phone = factory.Sequence(lambda n: "+3706%07d" % n)
    model_version = 1
    status = User.ACTIVE
    is_viisp_login = False
    viisp_company_code = None


class ManagerFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)

    first_name = factory.Faker("last_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttributeSequence(lambda o, n: "%s.%s%d@example.com" % (o.first_name, o.last_name, n))
    phone = factory.Sequence(lambda n: "+3706%07d" % n)
    organization = factory.SubFactory("vitrina.orgs.factories.OrganizationFactory")
