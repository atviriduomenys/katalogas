import factory
from factory.django import DjangoModelFactory

from vitrina.projects.models import Project


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project
        django_get_or_create = ('url',)

    url = factory.Faker('url')
    version = 1
