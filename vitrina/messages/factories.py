import factory
from factory.django import DjangoModelFactory

from vitrina.messages.models import Subscription
from vitrina.users.factories import UserFactory


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = Subscription

    user = factory.SubFactory(UserFactory)
    email_subscribed = True
