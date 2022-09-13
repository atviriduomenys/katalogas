import factory
from factory.django import DjangoModelFactory, ImageField

from vitrina.projects.models import Project


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = Project
        django_get_or_create = ('url',)

    url = factory.Faker('url')
    version = 1
    title = factory.Faker('catch_phrase')
    image = ImageField(filename="example.png")
