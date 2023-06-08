import factory
from factory.django import DjangoModelFactory

from vitrina.cms.factories import FilerImageFactory
from vitrina.projects.models import Project


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project
        django_get_or_create = ('url',)

    url = factory.Faker('url')
    version = 1
    title = factory.Faker('catch_phrase')
    image = factory.SubFactory(FilerImageFactory)
    status = Project.CREATED
