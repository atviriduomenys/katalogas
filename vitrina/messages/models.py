from datetime import datetime

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import utc
from django.db import models

from vitrina.users.models import User
from vitrina.datasets.models import Dataset

now = datetime.utcnow().replace(tzinfo=utc)


# TODO: https://github.com/jazzband/django-newsletter
class EmailTemplate(models.Model):
    created = models.DateTimeField(blank=True, null=True, default=now, editable=False)
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
        db_table = 'email_template'


class GlobalEmail(models.Model):
    created = models.DateTimeField(blank=True, null=True, default=now, editable=False)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    body = models.TextField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'global_email'


class NewsletterSubscription(models.Model):
    created = models.DateTimeField(blank=True, null=True, default=now, editable=False)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    email = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField()

    class Meta:
        managed = True
        db_table = 'newsletter_subscription'


class SentMail(models.Model):
    created = models.DateTimeField(blank=True, null=True, default=now, editable=False)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    recipient = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'sent_mail'


# TODO: Make generic.
class UserSubscription(models.Model):
    created = models.DateTimeField(blank=True, null=True, default=now, editable=False)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, db_column='dataset', blank=True, null=True)
    # dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)

    user = models.ForeignKey(User, models.DO_NOTHING, db_column='user', blank=True, null=True)
    # user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)

    active = models.BooleanField()

    class Meta:
        managed = True
        db_table = 'user_dataset_subscription'


class Subscription(models.Model):
    created = models.DateTimeField(default=now, editable=False)
    user = models.ForeignKey(User, models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'subscription'
        unique_together = ['user', 'content_type', 'object_id']

    def __str__(self):
        return str(self.user)
