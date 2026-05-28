import pytest
from unittest.mock import patch

from django.contrib.sites.models import Site
from django.utils import timezone

from vitrina.datasets.models import Dataset
from vitrina.messages.models import NewsletterSubscriber
from vitrina.messages.signals import send_monthly_newsletter
from djangocms_stories.models import Post, PostContent


def make_blog_post(date_published, title="Test Blog", slug="test-blog"):
    post = Post.objects.create(date_published=date_published)
    PostContent.objects.create(post=post, title=title, slug=slug, language="lt")
    return post


@pytest.fixture
def last_month():
    now = timezone.now()
    last_month = now.replace(day=1) - timezone.timedelta(days=1)
    return last_month.replace(day=15)


@pytest.fixture
def subscriber():
    return NewsletterSubscriber.objects.create(
        email="test@example.com",
        status=NewsletterSubscriber.SUBSCRIBED,
    )


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
@patch("djangocms_stories.models.PostContent.get_absolute_url")
def test_newsletter_with_blog_and_dataset(mock_get_absolute_url, mock_email, last_month, subscriber):
    mock_get_absolute_url.return_value = "/blog/test-blog/"
    make_blog_post(last_month, title="Test Blog", slug="test-blog")

    Dataset.objects.create(
        title="Test Dataset",
        description="Description here",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1


@pytest.mark.django_db
def test_no_content_yields_no_newsletter():
    NewsletterSubscriber.objects.create(
        email="empty@test.com",
        status=NewsletterSubscriber.SUBSCRIBED,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 0


@pytest.mark.django_db
def test_deleted_on_dataset_not_sent(last_month, subscriber):
    Dataset.objects.create(
        title="Hidden Dataset",
        description="...",
        created=last_month,
        deleted_on=timezone.now(),
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 0


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_unpublished_blog_post_not_included(mock_email, last_month, subscriber):
    # A post with no date_published won't match the last-month date filter
    post = Post.objects.create(date_published=None)
    PostContent.objects.create(post=post, title="Hidden Post", slug="hidden-post", language="lt")

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 0


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_multiple_subscribers_all_get_newsletter(mock_email, last_month):
    NewsletterSubscriber.objects.bulk_create(
        [
            NewsletterSubscriber(email="a@test.com", status=NewsletterSubscriber.SUBSCRIBED),
            NewsletterSubscriber(email="b@test.com", status=NewsletterSubscriber.SUBSCRIBED),
            NewsletterSubscriber(email="c@test.com", status=NewsletterSubscriber.UNSUBSCRIBED),
            NewsletterSubscriber(email="d@test.com", status=NewsletterSubscriber.PENDING),
        ]
    )

    Dataset.objects.create(
        title="Shared Dataset",
        description="Used for both",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 2


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_more_than_3_datasets_splits_correctly(mock_email, last_month, subscriber):
    for i in range(5):
        Dataset.objects.create(
            title=f"Dataset {i + 1}",
            description=f"Description {i + 1}",
            is_public=True,
            published=last_month,
            status=Dataset.HAS_DATA,
        )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    # Verify email was called with correct context structure
    call_args = mock_email.call_args
    context = call_args[1]["context"]

    # Should have exactly 3 top datasets and 2 list datasets
    assert len(context["top_datasets"]) == 3
    assert len(context["list_datasets"]) == 2
    assert "list_datasets" in context


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_exactly_3_datasets_no_list(mock_email, last_month, subscriber):
    for i in range(3):
        Dataset.objects.create(
            title=f"Dataset {i + 1}",
            description=f"Description {i + 1}",
            is_public=True,
            published=last_month,
            status=Dataset.HAS_DATA,
        )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    context = mock_email.call_args[1]["context"]
    assert len(context["top_datasets"]) == 3
    assert context.get("list_datasets") is None


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_private_datasets_excluded(mock_email, last_month, subscriber):
    Dataset.objects.create(
        title="Private Dataset",
        description="Should not appear",
        is_public=False,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    Dataset.objects.create(
        title="Public Dataset",
        description="Should appear",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    context = mock_email.call_args[1]["context"]
    assert len(context["top_datasets"]) == 1
    assert context["top_datasets"][0]["title"] == "Public Dataset"


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_current_month_content_excluded(mock_email, subscriber):
    now = timezone.now()

    Dataset.objects.create(
        title="Current Month Dataset",
        description="Should not appear",
        is_public=True,
        published=now,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 0  # No content should be included


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_email_sending_failure_continues(mock_email, last_month):
    subscribers = []
    for i in range(3):
        subscriber = NewsletterSubscriber.objects.create(
            email=f"test{i}@example.com",
            status=NewsletterSubscriber.SUBSCRIBED,
        )
        subscribers.append(subscriber)

    Dataset.objects.create(
        title="Test Dataset",
        description="Test",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    # Make the second email call fail
    mock_email.side_effect = [None, Exception("Email failed"), None]

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 2  # Should still send to 2 out of 3


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
@patch("djangocms_stories.models.PostContent.get_absolute_url")
def test_context_structure_blog_posts(mock_get_absolute_url, mock_email, last_month, subscriber):
    mock_get_absolute_url.return_value = "/blog/test-post/"
    make_blog_post(last_month, title="Test Blog Post", slug="test-post")

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    context = mock_email.call_args[1]["context"]
    blog_post = context["blog_posts"][0]

    assert "title" in blog_post
    assert "url" in blog_post
    assert "day" in blog_post
    assert "month" in blog_post
    assert blog_post["title"] == "Test Blog Post"
    assert blog_post["url"] == "/blog/test-post/"


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_context_structure_datasets(mock_email, last_month, subscriber):
    Dataset.objects.create(
        title="Test Dataset",
        description="Test description",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    context = mock_email.call_args[1]["context"]
    dataset = context["top_datasets"][0]

    assert "id" in dataset
    assert "title" in dataset
    assert "description" in dataset
    assert dataset["title"] == "Test Dataset"


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_month_year_formatting(mock_email, last_month, subscriber):
    Dataset.objects.create(
        title="Test Dataset",
        description="Test",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    context = mock_email.call_args[1]["context"]
    month_year = context["month_year"]

    assert str(timezone.now().year) in month_year
    lithuanian_months = [
        "sausis",
        "vasaris",
        "kovas",
        "balandis",
        "gegužė",
        "birželis",
        "liepa",
        "rugpjūtis",
        "rugsėjis",
        "spalis",
        "lapkritis",
        "gruodis",
    ]
    assert any(month in month_year for month in lithuanian_months)


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_unsubscribe_url_in_context(mock_email, last_month, subscriber):
    Dataset.objects.create(
        title="Test Dataset",
        description="Test",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    context = mock_email.call_args[1]["context"]
    unsubscribe_url = context["unsubscribe_url"]

    assert "unsubscribe" in unsubscribe_url
    assert str(subscriber.unsubscribe_token) in unsubscribe_url
    assert unsubscribe_url.startswith("https://")


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_domain_in_context(mock_email, last_month, subscriber):
    Dataset.objects.create(
        title="Test Dataset",
        description="Test",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    context = mock_email.call_args[1]["context"]
    domain = context["domain"]

    # Should be the current site's domain
    current_site = Site.objects.get_current()
    assert domain == current_site.domain


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
@patch("djangocms_stories.models.PostContent.get_absolute_url")
def test_only_blog_posts_no_datasets(mock_get_absolute_url, mock_email, last_month, subscriber):
    mock_get_absolute_url.return_value = "/blog/only-blog/"
    make_blog_post(last_month, title="Only Blog Post", slug="only-blog")

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    context = mock_email.call_args[1]["context"]
    assert "blog_posts" in context
    assert len(context["blog_posts"]) == 1
    assert "top_datasets" in context
    assert len(context["top_datasets"]) == 0


@pytest.mark.django_db
@patch("vitrina.messages.signals.email")
def test_only_datasets_no_blog_posts(mock_email, last_month, subscriber):
    Dataset.objects.create(
        title="Only Dataset",
        description="Test",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    count = send_monthly_newsletter.send(sender=None)[0][1]
    assert count == 1

    context = mock_email.call_args[1]["context"]
    assert "top_datasets" in context
    assert len(context["top_datasets"]) == 1
    assert "blog_posts" in context
    assert len(context["blog_posts"]) == 0


@pytest.mark.django_db
def test_no_subscribers_returns_early():
    last_month = timezone.now().replace(day=1) - timezone.timedelta(days=1)
    last_month = last_month.replace(day=15)

    Dataset.objects.create(
        title="Test Dataset",
        description="Test",
        is_public=True,
        published=last_month,
        status=Dataset.HAS_DATA,
    )

    # No subscribers created
    result = send_monthly_newsletter.send(sender=None)
    assert result[0][1] is None
