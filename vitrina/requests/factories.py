import factory
from factory.django import DjangoModelFactory

from vitrina.requests.models import Request


class RequestFactory(DjangoModelFactory):
    class Meta:
        model = Request
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
    version = 1
