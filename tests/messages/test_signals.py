import pytest
from unittest.mock import patch
from django.utils import timezone

from vitrina.datasets.models import Dataset
from vitrina.messages.models import NewsletterSubscriber
from vitrina.messages.signals import send_monthly_newsletter
from djangocms_blog.models import Post, BlogConfig


@pytest.fixture
def last_month():
    now = timezone.now()
    last_month = now.replace(day=1) - timezone.timedelta(days=1)
    return last_month.replace(day=15)


@pytest.fixture
def subscriber():
    return NewsletterSubscriber.objects.create(
        email='test@example.com',
        status=NewsletterSubscriber.SUBSCRIBED,
    )


@pytest.mark.django_db
@patch('vitrina.messages.signals.email')
@patch('djangocms_blog.models.Post.get_absolute_url')
def test_newsletter_with_blog_and_dataset(mock_get_absolute_url, mock_email, last_month, subscriber):
    mock_get_absolute_url.return_value = '/blog/test-blog/'
    Post.objects.create(
        title='Test Blog',
        slug='test-blog',
        publish=True,
        date_published=last_month,
        app_config=BlogConfig.objects.create(namespace="blog"),
    )

    Dataset.objects.create(
        title='Test Dataset',
        description='Description here',
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1


@pytest.mark.django_db
def test_no_content_yields_no_newsletter():
    NewsletterSubscriber.objects.create(
        email='empty@test.com',
        status=NewsletterSubscriber.SUBSCRIBED,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 0


@pytest.mark.django_db
def test_deleted_on_dataset_not_sent(last_month, subscriber):
    Dataset.objects.create(
        title='Hidden Dataset',
        description='...',
        created=last_month,
        deleted_on=timezone.now(),
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 0


@pytest.mark.django_db
@patch('vitrina.messages.signals.email')
def test_unpublished_blog_post_not_included(mock_email, last_month, subscriber):
    Post.objects.create(
        title='Hidden Post',
        slug='hidden-post',
        publish=False,
        date_published=last_month,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 0


@pytest.mark.django_db
@patch('vitrina.messages.signals.email')
def test_multiple_subscribers_all_get_newsletter(mock_email, last_month):
    NewsletterSubscriber.objects.bulk_create([
        NewsletterSubscriber(email='a@test.com', status=NewsletterSubscriber.SUBSCRIBED),
        NewsletterSubscriber(email='b@test.com', status=NewsletterSubscriber.SUBSCRIBED),
        NewsletterSubscriber(email='c@test.com', status=NewsletterSubscriber.UNSUBSCRIBED),
        NewsletterSubscriber(email='d@test.com', status=NewsletterSubscriber.PENDING),
    ])

    Dataset.objects.create(
        title='Shared Dataset',
        description='Used for both',
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 2
