import os

from django.db import models
from django.urls import reverse

from vitrina.datasets.models import Dataset


class Format(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    extension = models.TextField(blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    mimetype = models.TextField(blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'format'


class DistributionFormat(models.Model):
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    title = models.CharField(max_length=255, blank=True, null=True)
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'distribution_format'


class DatasetDistribution(models.Model):
    # TODO: https://github.com/atviriduomenys/katalogas/issues/59
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    modified = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.IntegerField()
    deleted = models.BooleanField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)

    identifier = models.CharField(max_length=255, blank=True, null=True)

    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    period_end = models.CharField(max_length=255, blank=True, null=True)
    period_start = models.CharField(max_length=255, blank=True, null=True)

    distribution_version = models.IntegerField(blank=True, null=True)

    municipality = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255, blank=True, null=True)

    type = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    url_format = models.ForeignKey('Format', models.DO_NOTHING, blank=True, null=True)

    filename = models.FileField(upload_to='data/', max_length=255, blank=True, null=True)
    issued = models.CharField(max_length=255, blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey(Dataset, models.DO_NOTHING, blank=True, null=True)
    access_url = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'dataset_distribution'

    def extension(self):
        if self.filename:
            name, extension = os.path.splitext(self.filename.name)
            return extension.replace(".", "").upper()
        return ""

    def filename_without_path(self):
        return os.path.basename(self.filename.name) if self.filename else ""

    def get_download_url(self):
        return reverse('dataset-distribution-download', kwargs={
            'organization_kind': self.dataset.organization.kind if self.dataset and self.dataset.organization else None,
            'organization_slug': self.dataset.organization.slug if self.dataset and self.dataset.organization else None,
            'dataset_slug': self.dataset.slug if self.dataset else None,
            'pk': self.pk,
            'filename': self.filename_without_path()
        })

