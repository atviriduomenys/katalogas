import datetime

import factory
from factory.django import DjangoModelFactory

from vitrina.tasks.models import Task


class TaskFactory(DjangoModelFactory):
    class Meta:
        model = Task
        django_get_or_create = ('title',)

    title = factory.Faker('catch_phrase')
