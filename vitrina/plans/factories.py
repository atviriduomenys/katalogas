import factory
from factory.django import DjangoModelFactory

from vitrina.orgs.factories import OrganizationFactory
from vitrina.plans.models import Plan


class PlanFactory(DjangoModelFactory):
    class Meta:
        model = Plan
        django_get_or_create = ('title',)

    title = factory.Faker('word')
    receiver = factory.SubFactory(OrganizationFactory)
