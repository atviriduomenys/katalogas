import logging
from datetime import timedelta
from django.conf import settings
from django.dispatch import receiver, Signal
from django.utils import timezone
from django.contrib.sites.models import Site
from django.urls import reverse
from djangocms_stories.models import PostContent

from vitrina.messages.models import NewsletterSubscriber
from vitrina.datasets.models import Dataset
from vitrina.helpers import email

logger = logging.getLogger(__name__)
send_monthly_newsletter = Signal()


@receiver(send_monthly_newsletter)
def send_newsletter_to_subscribers(sender, **kwargs):
    context = {}
    list_datasets = None
    top_dataset_to_show = 3
    now = timezone.now()
    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = first_day_this_month - timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    subscribers = NewsletterSubscriber.objects.filter(status=NewsletterSubscriber.SUBSCRIBED)
    if not subscribers.exists():
        logger.warning("No subscribers found.")
        return

    blog_posts = PostContent.admin_manager.filter(
        post__date_published__gte=last_month_start,
        post__date_published__lte=last_month_end,
        language=settings.LANGUAGE_CODE,
    ).order_by("-post__date_published")

    datasets = Dataset.objects.filter(
        is_public=True,
        published__gte=last_month_start,
        published__lte=last_month_end,
        deleted_on__isnull=True,
        deleted__isnull=True,
    )

    if not blog_posts and not datasets:
        return 0

    if len(datasets) > top_dataset_to_show:
        top_datasets = datasets[:top_dataset_to_show]
        list_datasets = datasets[top_dataset_to_show:]
    else:
        top_datasets = datasets[:top_dataset_to_show]

    domain = Site.objects.get_current().domain
    context["domain"] = domain

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
    context["month_year"] = month_year

    blog_posts_data = [
        {
            "title": post.title,
            "url": post.get_absolute_url(),
            "day": post.date_published.day,
            "month": month_names[post.date_published.month],
        }
        for post in blog_posts
    ]
    context["blog_posts"] = blog_posts_data
    top_datasets_data = [
        {
            "id": dataset.id,
            "title": dataset.title,
            "description": dataset.description,
        }
        for dataset in top_datasets
    ]
    context["top_datasets"] = top_datasets_data
    if list_datasets:
        list_datasets_data = [
            {
                "id": dataset.id,
                "title": dataset.title,
                "description": dataset.description,
                "day": dataset.published.day,
                "month": month_names[dataset.published.month],
            }
            for dataset in list_datasets
        ]
        context["list_datasets"] = list_datasets_data

    sent_count = 0
    for subscriber in subscribers:
        unsubscribe_url = (
            f"https://{domain}{reverse('newsletter-unsubscribe', kwargs={'token': subscriber.unsubscribe_token})}"
        )

        context["unsubscribe_url"] = unsubscribe_url

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
