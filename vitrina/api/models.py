from django.db import models

from vitrina.orgs.models import Organization, Representative


class ApiKey(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField(default=1)

    api_key = models.CharField(max_length=255, blank=True, null=True)
    enabled = models.BooleanField(blank=True, null=True)
    expires = models.DateTimeField(blank=True, null=True)
    representative = models.ForeignKey(Representative, models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'api_key'


class ApiDescription(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField(default=1)

    api_version = models.CharField(blank=True, null=True, max_length=255)
    contact_email = models.CharField(blank=True, null=True, max_length=255)
    contact_name = models.CharField(blank=True, null=True, max_length=255)
    contact_url = models.CharField(blank=True, null=True, max_length=255)
    desription_html = models.TextField(blank=True, null=True)
    identifier = models.CharField(blank=True, null=True, max_length=255)
    licence = models.CharField(blank=True, null=True, max_length=255)
    licence_url = models.CharField(blank=True, null=True, max_length=255)
    title = models.CharField(blank=True, null=True, max_length=255)

    class Meta:
        managed = False
        db_table = 'api_description'