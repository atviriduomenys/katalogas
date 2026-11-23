import factory
from factory.django import DjangoModelFactory

from vitrina.messages.models import Subscription, MassMail
from vitrina.users.factories import UserFactory


class SubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = Subscription

    user = factory.SubFactory(UserFactory)
    email_subscribed = True


class MassMailFactory(DjangoModelFactory):
    class Meta:
        model = MassMail

    email_subject = factory.Faker("catch_phrase")
    email_content = factory.Faker("catch_phrase")
    recipients = "test@example.com"
