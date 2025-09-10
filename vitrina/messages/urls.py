from django.urls import path

from vitrina.messages.views import (
    UnsubscribeView,
    SubscribeFormView,
    NewsletterSubscribeView,
    NewsletterUnsubscribeView,
    NewsletterConfirmView,
)

urlpatterns = [
    path(
        "unsubscribe/<int:content_type_id>/<int:obj_id>/<int:user_id>/",
        UnsubscribeView.as_view(),
        name="unsubscribe",
    ),
    path(
        "subscription_form/<int:content_type_id>/<int:obj_id>/<int:user_id>/",
        SubscribeFormView.as_view(),
        name="subscribe-form",
    ),
    path(
        "newsletter/subscribe/",
        NewsletterSubscribeView.as_view(),
        name="newsletter-subscribe",
    ),
    path(
        "newsletter/confirm/<uuid:token>/",
        NewsletterConfirmView.as_view(),
        name="newsletter-confirm",
    ),
    path(
        "newsletter/unsubscribe/<uuid:token>/",
        NewsletterUnsubscribeView.as_view(),
        name="newsletter-unsubscribe",
    ),
]
