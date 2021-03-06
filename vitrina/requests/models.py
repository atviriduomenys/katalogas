from django.db import models
from django.contrib.auth.models import User

from django.urls import reverse

from vitrina.orgs.models import Organization
from vitrina.requests.managers import PublicRequestManager


class Request(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    comment = models.TextField(blank=True, null=True)
    dataset_id = models.BigIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    format = models.CharField(max_length=255, blank=True, null=True)
    is_existing = models.TextField()  # This field type is a guess.
    notes = models.TextField(blank=True, null=True)
    organization = models.ForeignKey(Organization, models.DO_NOTHING, blank=True, null=True)
    periodicity = models.CharField(max_length=255, blank=True, null=True)
    planned_opening_date = models.DateField(blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    uuid = models.CharField(unique=True, max_length=36, blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    changes = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.TextField()  # This field type is a guess.
    structure_data = models.TextField(blank=True, null=True)
    structure_filename = models.CharField(max_length=255, blank=True, null=True)

    objects = models.Manager()
    public = PublicRequestManager()

    class Meta:
        managed = False
        db_table = 'request'

    def get_absolute_url(self):
        return reverse('request-detail', kwargs={'pk': self.pk})


# TODO: https://github.com/atviriduomenys/katalogas/issues/59
class RequestEvent(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    meta = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    request = models.ForeignKey(Request, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'request_event'


# TODO: https://github.com/atviriduomenys/katalogas/issues/14
class RequestStructure(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    data_notes = models.CharField(max_length=255, blank=True, null=True)
    data_title = models.CharField(max_length=255, blank=True, null=True)
    data_type = models.CharField(max_length=255, blank=True, null=True)
    dictionary_title = models.CharField(max_length=255, blank=True, null=True)
    request_id = models.BigIntegerField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'request_structure'
