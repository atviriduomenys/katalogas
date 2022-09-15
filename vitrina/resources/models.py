import os
import pathlib

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
        return pathlib.Path(self.filename.name).suffix.lstrip('.').upper() if self.filename else ""

    def filename_without_path(self):
        return pathlib.Path(self.filename.name).name if self.filename else ""

    def is_external_url(self):
        return self.type == "URL"

    def get_download_url(self):
        if self.is_external_url():
            return self.url
        return reverse('dataset-distribution-download', kwargs={
            'dataset_id': self.dataset.pk,
            'distribution_id': self.pk,
            'filename': self.filename_without_path()
        })

    def get_format(self):
        if self.is_external_url():
            return self.url_format
        else:
            if not self.filename:
                return self.mime_type
            elif self.url_format:
                return self.url_format
            else:
                return self.extension()

    def is_previewable(self):
        return (self.extension() == "CSV" or self.extension() == "XLSX") and self.filename.file.size > 0

