from django.db import models

from vitrina.orgs.models import Organization
from vitrina.classifiers.models import Licence


class Catalog(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    identifier = models.CharField(unique=True, max_length=255, blank=True, null=True)
    slug = models.CharField(unique=True, max_length=255, blank=True, null=True)

    title = models.TextField(blank=True, null=True)
    title_en = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    licence = models.ForeignKey(Licence, models.PROTECT, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'catalog'

    def __str__(self):
        return self.title


class HarvestingJob(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    indexed = models.BooleanField(blank=True, null=True)
    schedule = models.CharField(max_length=255, blank=True, null=True)
    started = models.DateTimeField(blank=True, null=True)
    stopped = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    translated = models.BooleanField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    organization = models.ForeignKey(Organization, models.CASCADE, db_column='organization', blank=True, null=True)
    active = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'harvesting_job'

    def __str__(self):
        return f"{self.title}"
