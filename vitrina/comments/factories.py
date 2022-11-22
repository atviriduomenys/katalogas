import factory
from factory.django import DjangoModelFactory

from vitrina.comments.models import Comment
from vitrina.users.factories import UserFactory


class CommentFactory(DjangoModelFactory):
    class Meta:
        model = Comment
        django_get_or_create = ('user', 'body',)

    user = factory.SubFactory(UserFactory)
    body = factory.Faker('catch_phrase')
    type = Comment.USER

