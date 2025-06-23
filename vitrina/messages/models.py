import uuid
from datetime import timedelta

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from vitrina.users.models import User

from django.utils.translation import gettext_lazy as _


# TODO: https://github.com/jazzband/django-newsletter
class EmailTemplate(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    identifier = models.CharField(unique=True, max_length=255, blank=True, null=True)
    template = models.TextField(blank=True, null=True)
    variables = models.TextField(blank=True, null=True)
    subject = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "email_template"


class GlobalEmail(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "global_email"


class NewsletterSubscription(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    email = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField()

    class Meta:
        managed = True
        db_table = "newsletter_subscription"


class SentMail(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    recipient = models.TextField(blank=True, null=True, verbose_name=_("Gavėjas"))
    email_subject = models.TextField(blank=True, null=True, verbose_name="Tema")
    email_content = models.TextField(blank=True, null=True, verbose_name="Turinys")
    email_sent = models.BooleanField(blank=True, null=True, verbose_name="Išsiųsta")
    identifier = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("Identifikatorius")
    )

    class Meta:
        managed = True
        db_table = "sent_mail"


# TODO: Make generic.
class UserSubscription(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    dataset = models.ForeignKey(
        Dataset, models.CASCADE, db_column="dataset", blank=True, null=True
    )
    # dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)

    user = models.ForeignKey(
        User, models.CASCADE, db_column="user", blank=True, null=True
    )
    # user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)

    active = models.BooleanField()

    class Meta:
        managed = True
        db_table = "user_dataset_subscription"


class Subscription(models.Model):
    ORGANIZATION = "ORGANIZATION"
    DATASET = "DATASET"
    REQUEST = "REQUEST"
    PROJECT = "PROJECT"
    COMMENT = "COMMENT"
    SUB_TYPE_CHOICES = (
        (ORGANIZATION, _("Organizacijos prenumerata")),
        (DATASET, _("Duomenų rinkinio prenumerata")),
        (REQUEST, _("Poreikio prenumerata")),
        (PROJECT, _("Projekto prenumerata")),
        (COMMENT, _("Komentaro prenumerata")),
    )

    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    sub_type = models.CharField(
        max_length=255,
        choices=SUB_TYPE_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("Prenumeratos tipas"),
    )
    email_subscribed = models.BooleanField(
        default=False, verbose_name=_("Prenumeratos laiško užsisakymas")
    )
    dataset_update_sub = models.BooleanField(
        default=False, verbose_name=_("Susijusių duomenų rinkinių prenumerata")
    )
    dataset_comments_sub = models.BooleanField(
        default=False, verbose_name=_("Duomenų rinkinių komentarų prenumerata")
    )
    request_update_sub = models.BooleanField(
        default=False, verbose_name=_("Susijusių poreikių prenumerata")
    )
    request_comments_sub = models.BooleanField(
        default=False, verbose_name=_("Poreikių komentarų prenumerata")
    )
    project_update_sub = models.BooleanField(
        default=False, verbose_name=_("Susijusių projektų prenumerata")
    )
    project_comments_sub = models.BooleanField(
        default=False, verbose_name=_("Projektų komentarų prenumerata")
    )
    comment_replies_sub = models.BooleanField(
        default=False, verbose_name=_("Komentaro atsako prenumerata")
    )

    class Meta:
        db_table = "subscription"
        unique_together = ["user", "content_type", "object_id"]

    def __str__(self):
        return str(self.user)

    def get_absolute_url(self):
        if self.content_object:
            return self.content_object.get_absolute_url()
        else:
            return None


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created = models.DateTimeField(auto_now_add=True)
    is_confirmed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    confirmation_token = models.UUIDField(
        default=uuid.uuid4, unique=True, null=True, blank=True
    )
    confirmation_expires_at = models.DateTimeField(null=True, blank=True)

    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True)

    def save(self, *args, **kwargs):
        if not self.is_confirmed and not self.confirmation_expires_at:
            self.confirmation_expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_confirmation_expired(self):
        if self.is_confirmed or not self.confirmation_expires_at:
            return False
        return timezone.now() > self.confirmation_expires_at

    def confirm_subscription(self):
        self.is_confirmed = True
        self.confirmation_token = None
        self.confirmation_expires_at = None
        self.save()

    def __str__(self):
        status = "confirmed" if self.is_confirmed else "pending"
        return f"{self.email} ({status})"
