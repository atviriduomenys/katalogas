import logging
from datetime import timedelta
from django.dispatch import receiver, Signal
from django.utils import timezone
from django.contrib.sites.models import Site
from django.urls import reverse
from djangocms_blog.models import Post

from vitrina.messages.models import NewsletterSubscriber
from vitrina.datasets.models import Dataset
from vitrina.helpers import email

logger = logging.getLogger(__name__)
send_monthly_newsletter = Signal()


@receiver(send_monthly_newsletter)
def send_newsletter_to_subscribers(sender, **kwargs):
    last_month_start = timezone.now().replace(day=1) - timedelta(days=1)
    last_month_start = last_month_start.replace(day=1)
    last_month_end = timezone.now().replace(day=1) - timedelta(seconds=1)

    blog_posts = Post.objects.filter(
        publish=True,
        date_published__gte=last_month_start,
        date_published__lte=last_month_end,
    ).order_by("-date_published")

    datasets = Dataset.objects.filter(
        is_public=True,
        published__gte=last_month_start,
        published__lte=last_month_end,
        soft_deleted__isnull=True,
        deleted__isnull=True,
    )

    if not blog_posts and not datasets:
        return 0

    subscribers = NewsletterSubscriber.objects.filter(is_confirmed=True, is_active=True)

    domain = Site.objects.get_current().domain

    month_names = {
        1: "sausis",
        2: "vasaris",
        3: "kovas",
        4: "balandis",
        5: "gegužė",
        6: "birželis",
        7: "liepa",
        8: "rugpjūtis",
        9: "rugsėjis",
        10: "spalis",
        11: "lapkritis",
        12: "gruodis",
    }
    current_month = timezone.now().month
    current_year = timezone.now().year
    month_year = f"{current_year} m. {month_names[current_month]}"

    blog_posts_data = [
        {
            "title": getattr(post, "title", ""),
            "url": post.get_absolute_url(),
            "day": post.date_published.day,
            "month": month_names[post.date_published.month],
        }
        for post in blog_posts
    ]

    datasets_data = [
        {
            "id": dataset.id,
            "title": dataset.title,
            "description": dataset.description,
            "status_display": dataset.get_status_display(),
        }
        for dataset in datasets
    ]

    sent_count = 0
    for subscriber in subscribers:
        unsubscribe_url = (
            f"https://{domain}"
            f"{reverse('newsletter-unsubscribe', kwargs={'token': subscriber.unsubscribe_token})}"
        )

        context = {
            "month_year": month_year,
            "blog_posts": blog_posts_data,
            "datasets": datasets_data,
            "domain": domain,
            "unsubscribe_url": unsubscribe_url,
        }

        try:
            email(
                recipients=[subscriber.email],
                email_identifier="monthly_newsletter",
                name="vitrina/messages/emails/newsletter/newsletter.md",
                context=context,
            )
            sent_count += 1
        except Exception as e:
            logger.error("Failed to send newsletter email", exc_info=e)
            continue

    return sent_count
