from django.db import models

from django.urls import reverse
from vitrina.datasets.models import Dataset
from vitrina.orgs.models import Representative, Organization
from django.utils.translation import gettext_lazy as _

from vitrina.projects.models import Project


class ApiKey(models.Model):
    DUPLICATE = "DUPLICATE"

    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField(default=1)

    api_key = models.CharField(max_length=255, blank=True, null=True, unique=True)
    enabled = models.BooleanField(blank=True, null=True)
    expires = models.DateTimeField(blank=True, null=True)
    representative = models.ForeignKey(
        Representative,
        models.CASCADE,
        blank=True,
        null=True,
    )
    organization = models.ForeignKey(
        Organization,
        models.CASCADE,
        blank=True,
        null=True
    )
    project = models.ForeignKey(
        Project,
        models.CASCADE,
        blank=True,
        null=True
    )
    client_id = models.CharField(blank=True, null=True, max_length=255)
    client_name = models.CharField(blank=True, null=True, max_length=255)

    class Meta:
        db_table = 'api_key'

    def get_absolute_url(self):
        return reverse('organization-apikeys-detail', kwargs={
            'pk': self.organization.pk,
            'apikey_id': self.pk
        })

    def __str__(self):
        return self.api_key


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


class ApiScope(models.Model):
    enabled = models.BooleanField(blank=True, null=True, default=True)
    key = models.ForeignKey(
        ApiKey,
        models.CASCADE,
        verbose_name=_('API raktas')
    )
    scope = models.CharField(max_length=255, verbose_name=_('Taikymo sritis'))
    organization = models.ForeignKey(
        Organization,
        models.CASCADE,
        blank=True,
        null=True,
        verbose_name=_('Organizacija')
    )
    dataset = models.ForeignKey(
        Dataset,
        models.CASCADE,
        blank=True,
        null=True,
        verbose_name=_('Duomenų rinkinys')
    )

    class Meta:
        db_table = 'api_scope'

    def __str__(self):
        return self.scope
