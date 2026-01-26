import pytest
from datetime import timedelta
from django.utils import timezone
from django.db import IntegrityError

from vitrina.messages.models import NewsletterSubscriber


@pytest.mark.django_db
class TestNewsletterSubscriber:
    def test_create_newsletter_subscriber(self):
        subscriber = NewsletterSubscriber.objects.create(email="test@example.com")
        subscriber.initiate_subscription()

        assert subscriber.email == "test@example.com"
        assert subscriber.status == NewsletterSubscriber.PENDING
        assert subscriber.confirmation_token is not None
        assert subscriber.confirmation_expires_at is not None
        assert subscriber.unsubscribe_token is not None
        assert subscriber.created is not None

    @pytest.mark.parametrize(
        "email_variant",
        [
            "test@example.com",
            "tEST@example.com",
        ],
    )
    def test_unique_email_constraint(self, email_variant):
        NewsletterSubscriber.objects.create(email="test@example.com")

        with pytest.raises(IntegrityError):
            NewsletterSubscriber.objects.create(email=email_variant)

    def test_auto_set_confirmation_expiry(self):
        before_creation = timezone.now()
        expected_expiry = before_creation + timedelta(hours=24)
        subscriber = NewsletterSubscriber.objects.create(
            email="test@example.com", confirmation_expires_at=expected_expiry
        )
        actual_expiry = subscriber.confirmation_expires_at

        tolerance = timedelta(minutes=1)
        assert abs(actual_expiry - expected_expiry) < tolerance

    def test_is_confirmation_expired_false_when_not_expired(self):
        future_time = timezone.now() + timedelta(hours=1)
        subscriber = NewsletterSubscriber.objects.create(email="test@example.com", confirmation_expires_at=future_time)

        assert subscriber.is_confirmation_expired() is False

    def test_is_confirmation_expired_true_when_expired(self):
        past_time = timezone.now() - timedelta(hours=1)
        subscriber = NewsletterSubscriber.objects.create(email="test@example.com", confirmation_expires_at=past_time)

        assert subscriber.is_confirmation_expired() is True

    def test_is_confirmation_expired_when_already_subscribed(self):
        subscriber = NewsletterSubscriber.objects.create(
            email="test@example.com",
        )
        subscriber.confirm_subscription()

        assert subscriber.is_confirmation_expired() is True

    def test_confirm_subscription(self):
        subscriber = NewsletterSubscriber.objects.create(email="test@example.com")
        subscriber.initiate_subscription()

        assert subscriber.status == NewsletterSubscriber.PENDING
        assert subscriber.confirmation_token is not None
        assert subscriber.confirmation_expires_at is not None

        subscriber.confirm_subscription()

        assert subscriber.status == NewsletterSubscriber.SUBSCRIBED
        assert subscriber.confirmation_token is None
        assert subscriber.confirmation_expires_at is None

    def test_string_representation(self):
        pending = NewsletterSubscriber.objects.create(email="pending@example.com")
        assert str(pending) == "pending@example.com (pending)"

        confirmed = NewsletterSubscriber.objects.create(
            email="confirmed@example.com", status=NewsletterSubscriber.SUBSCRIBED
        )
        assert str(confirmed) == "confirmed@example.com (subscribed)"

    def test_deactivate_subscription(self):
        subscriber = NewsletterSubscriber.objects.create(
            email="test@example.com", status=NewsletterSubscriber.SUBSCRIBED
        )

        subscriber.unsubscribe()

        assert subscriber.status == NewsletterSubscriber.UNSUBSCRIBED

    def test_multiple_token_generation(self):
        subscriber1 = NewsletterSubscriber.objects.create(email="test1@example.com")
        subscriber2 = NewsletterSubscriber.objects.create(email="test2@example.com")

        assert subscriber1.confirmation_token != subscriber2.confirmation_token
        assert subscriber1.unsubscribe_token != subscriber2.unsubscribe_token
